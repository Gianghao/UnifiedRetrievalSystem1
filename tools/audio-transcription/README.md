# Audio and video transcription

This local experiment converts an audio or video recording into timestamped text
with source IDs. It is a processing handoff for Tài, Quân, Thiện, and Xuân Ngân.
Automatic processing after uploads remains planned application integration.

## Pilot configuration

The pilot uses the multilingual Whisper small model through faster-whisper,
running on Windows CPU with int8 computation, two threads, and one worker.
The model revision and inference settings are written into every output.
The team's proposed Whisper large-v3 research baseline is a separate run to
coordinate with Hào. Results from these model configurations need distinct labels.

Vietnamese remains the default language. All modes use `task=transcribe` to
preserve the spoken language. The output is UTF-8 JSON, including Vietnamese
diacritics. Transcription quality
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

### Export video to JSON

```powershell
$videoPath = Read-Host 'Video file path'
.\.venv\Scripts\python.exe tools/audio-transcription/transcribe_audio.py $videoPath --video --language vi --output .local-research/video-transcript.json
```

The tool transcribes the first audio track of a video, such as an MP4 or WebM.
PyAV decodes the track in memory using the existing dependencies. The export
covers spoken words. Files with no audio track produce an error and preserve
any existing output. Use the same language and provenance options as for audio.

## Language handling

Select a language mode with `--language`.

| Value | Recognizer behavior | Language metadata |
|---|---|---|
| `vi` | Explicit Vietnamese, the default | `language=vi`, `language_source=explicit` |
| `en` | Explicit English | `language=en`, `language_source=explicit` |
| Another supported code, such as `fr` | Explicit requested language | Records the requested code |
| `auto` | Detects a language from the initial audio window, then uses it for decoding | Records the initially detected language and probability |
| `mixed` | Splits speech at pauses and detects language for each region | Records region/segment language estimates and `language_mode=mixed` |

The multilingual model is used in every mode. Fixed language selection supplies
a decoder language token. English words can still occur in Vietnamese speech.

For a chosen `$audioPath`, run the appropriate command. Separate output names
keep experimental conditions inspectable.

```powershell
.\.venv\Scripts\python.exe tools/audio-transcription/transcribe_audio.py $audioPath --language en --output .local-research/audio-english.json --offline
.\.venv\Scripts\python.exe tools/audio-transcription/transcribe_audio.py $audioPath --language auto --output .local-research/audio-auto.json --offline
.\.venv\Scripts\python.exe tools/audio-transcription/transcribe_audio.py $audioPath --language mixed --output .local-research/audio-mixed.json --offline
```

Automatic mode passes `language=None` to faster-whisper. Its `language` field
describes the initial detection and `language_source=detected_initial_window`.
`initial_language_probability` records that initial classifier result.

Mixed mode uses bundled Silero voice-activity detection to find speech regions.
It splits at pauses of at least 400 ms, adds 100 ms of speech padding, and limits
regions to 30 seconds. Each region is transcribed with automatic language
detection. Original sample offsets are added back to every returned timestamp,
so citations retain positions in the complete source recording.

Mixed output includes `speech_regions` and `languages_detected`. Its top-level
`language` is the detected code for one language, `mul` for multiple detected
languages, or `und` when no speech regions are found. Its `language_source` is
`detected_per_speech_region`. Each segment records its region's language estimate,
probability, and `language_scope=speech_region`.

The mixed strategy and VAD settings are recorded under
`processor.mixed_language_processing`. Speech regions can still contain language
switches, and their language labels describe the region's detected language.
Review natural code-switching examples to evaluate recognition and segmentation.
Classifier probabilities describe language estimates. Transcription accuracy
needs comparison with reviewed words.

`language_mode` and `language_requested` are additive fields. The existing
Vietnamese command retains its default behavior, source metadata, and output
shape. Python callers can also pass `language=None` for automatic mode.

## Read the result

The document contains the recording's source identity, SHA-256, duration,
language, ASR variant, software/model versions, inference settings, timings,
and a `segments` array. Each segment has its own ID, text, and start/end seconds
relative to the complete original recording. Fixed/automatic modes process the
recording directly. Mixed mode restores each speech region's original offset.
Small timestamp overshoots up to 0.1 seconds are clipped to the audio interval's
actual duration.

Video exports use `source_type: "video"`, the original video filename and
checksum, and the same `segments` format as audio. `audio_stream_index` identifies
the selected container stream, and `audio_start_seconds` gives the start of the
decoded track on the video's playback timeline. Segment and speech-region times
use that same timeline. `duration_seconds` gives the end of the decoded audio
on the playback timeline, which can precede the last video frame.

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

The synthetic checks exercise fixed Vietnamese/English, automatic and mixed
language settings, supported-code compatibility, UTF-8 output, source
IDs/checksums, mixed-region offsets and unique IDs, silence handling, timestamp
validation, and failure-path/source protection. Video checks cover delayed audio,
gaps in the audio track, and a video without audio.
They use a mocked recognizer and the cached-model interface without a download.
Run an actual recording separately to evaluate model output and runtime.

For a small local functionality check, use a Vietnamese recording, an English
recording, and a file containing both languages. A synthesized English recording
and a concatenated mixed sample can exercise the pipeline during development.
Record how these samples were constructed. A human-reviewed code-switching
corpus is needed for research conclusions about recognition quality.

## Sources

- [Whisper models, languages, and transcription](https://github.com/openai/whisper)
- [faster-whisper implementation and CPU int8 usage](https://github.com/SYSTRAN/faster-whisper)
- [Converted multilingual small model](https://huggingface.co/Systran/faster-whisper-small)
