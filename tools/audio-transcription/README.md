# Vietnamese audio transcription experiment

This local experiment converts a recording into timestamped Vietnamese text
with source IDs. It is a processing handoff for Tài, Quân, Thiện, and Xuân Ngân.
Automatic processing after uploads remains planned application integration.

## Pilot configuration

The pilot uses the multilingual Whisper small model through faster-whisper,
running on Windows CPU with int8 computation, two threads, and one worker.
The model revision and inference settings are written into every output.
The team's proposed Whisper large-v3 research baseline is a separate run to
coordinate with Hào. Results from these model configurations need distinct labels.

Set the spoken language explicitly to `vi` and use `task=transcribe` to preserve
Vietnamese text and diacritics. The output is UTF-8 JSON. Transcription quality
depends on the recording, speaker, accent, vocabulary, and model configuration.

The model files download from the model publisher into `.local-research/models`
on D: for this checkout. Inference reads the local recording. The runtime lives
in the project's Windows `.venv`; WSL's memory cap applies to WSL workloads.

## Run from PowerShell

Open PowerShell in the repository root. The shared project `.venv` can be reused.
For a fresh checkout, follow the environment instructions in the PDF experiment
and install the audio dependencies.

```powershell
.\.venv\Scripts\python.exe -m pip install -r tools/audio-transcription/requirements.txt
```

List the real input filenames, then enter the path of the recording to process.

```powershell
Get-ChildItem -LiteralPath '.local-research/input' -File | ForEach-Object { $_.FullName }
$audioPath = Read-Host 'Audio file path'
.\.venv\Scripts\python.exe tools/audio-transcription/transcribe_audio.py $audioPath --language vi --output .local-research/audio-transcript.json
```

For a chat attachment, also pass its message UUID with `--source-id` and its
conversation UUID with `--conversation-id`. These IDs retain provenance.
The application must enforce membership when files and results are integrated.

After the first model download, `--offline` uses the pinned cached model.
Rerunning replaces the requested transcript output after successful extraction.
Opening or decoding failures preserve an existing output. The source recording
cannot be used as the output path.

## Read the result

The document contains the recording's source identity, SHA-256, duration,
language, ASR variant, software/model versions, inference settings, timings,
and a `segments` array. Each segment has its own ID, text, and start/end seconds
relative to the complete original recording. Voice-activity filtering is disabled,
so preprocessing leaves the source time axis intact. Small timestamp overshoots
up to 0.1 seconds are clipped to the actual recording duration.

The ASR output is marked `unreviewed`. Listen to the source intervals to verify
both words and timestamps before using them as benchmark evidence. An empty
segment list is recorded as `no_speech_detected` and needs review.

For the corrected reference, retain source/segment IDs and intervals, and have
a reviewer enter what is audible. Save review status and uncertain speech.
WER requires a reviewed reference plus an agreed normalization/tokenization rule.
For Vietnamese, decide whether scoring units are whitespace-separated syllables
or segmented words and record that choice. Preserve the original accented text
in the stored transcript.

Original recordings, transcript JSON, model files, reference drafts, and local
download caches belong under the ignored `.local-research/` folder. Their
retention is managed separately from the app's attachment expiration.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tools/audio-transcription -p 'test_*.py' -v
```

The synthetic checks exercise Vietnamese transcription settings, UTF-8 output,
source IDs/checksums, timestamp validation, and failure-path/source protection.
They use a mocked recognizer and the cached-model interface without a download.
Run an actual recording separately to evaluate model output and runtime.

## Sources

- [Whisper models, languages, and transcription](https://github.com/openai/whisper)
- [faster-whisper implementation and CPU int8 usage](https://github.com/SYSTRAN/faster-whisper)
- [Converted multilingual small model](https://huggingface.co/Systran/faster-whisper-small)
