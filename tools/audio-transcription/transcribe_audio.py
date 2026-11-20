"""Transcribe local audio or a video's audio track to timestamped JSON."""

import argparse
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import time


MODEL_ID = "Systran/faster-whisper-small"
MODEL_REVISION = "536b0662742c02347bc0e980a01041f333bce120"
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / ".local-research" / "models"
SAMPLE_RATE = 16000
MIXED_VAD_SETTINGS = {
    "min_silence_duration_ms": 400,
    "speech_pad_ms": 100,
    "max_speech_duration_s": 30,
}


def segment_records(raw_segments, source_id: str, duration: float) -> list[dict]:
    """Retain the model's source-time intervals and reject invalid locations."""
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("The audio must have a positive, finite duration.")
    records = []
    for index, segment in enumerate(raw_segments, start=1):
        text = segment.text.strip()
        if not text:
            continue
        start = float(segment.start)
        end = float(segment.end)
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or start >= duration
            or end <= start
            or end > duration + 0.1
        ):
            raise ValueError(f"Invalid source timestamps in segment {index}.")
        records.append(
            {
                "source_id": source_id,
                "segment_id": f"{source_id}:segment:{index:04d}",
                "start_seconds": round(start, 3),
                "end_seconds": round(min(end, duration), 3),
                "text": text,
            }
        )
    return records


def transcribe_mixed(model, audio, source_id: str, settings: dict):
    """Detect language per speech region and restore original-file time offsets."""
    from faster_whisper.audio import decode_audio
    from faster_whisper.vad import get_speech_timestamps, VadOptions

    if isinstance(audio, str):
        audio = decode_audio(audio, sampling_rate=SAMPLE_RATE)
    duration = len(audio) / SAMPLE_RATE
    if duration <= 0:
        raise ValueError("The audio must have a positive duration.")
    speech_ranges = get_speech_timestamps(
        audio,
        vad_options=VadOptions(**MIXED_VAD_SETTINGS),
        sampling_rate=SAMPLE_RATE,
    )
    segments = []
    regions = []
    for index, speech_range in enumerate(speech_ranges, start=1):
        start_sample = speech_range["start"]
        end_sample = speech_range["end"]
        offset = start_sample / SAMPLE_RATE
        region_duration = (end_sample - start_sample) / SAMPLE_RATE
        raw_segments, info = model.transcribe(audio[start_sample:end_sample], **settings)
        region_segments = segment_records(raw_segments, source_id, region_duration)
        region_id = f"{source_id}:region:{index:04d}"
        probability = float(info.language_probability)
        regions.append(
            {
                "region_id": region_id,
                "start_seconds": round(offset, 3),
                "end_seconds": round(end_sample / SAMPLE_RATE, 3),
                "language": info.language,
                "language_probability": probability,
            }
        )
        for segment in region_segments:
            segment["segment_id"] = f"{source_id}:segment:{len(segments) + 1:04d}"
            segment["start_seconds"] = round(offset + segment["start_seconds"], 3)
            segment["end_seconds"] = round(
                min(duration, offset + segment["end_seconds"]), 3
            )
            segment["language"] = info.language
            segment["language_probability"] = probability
            segment["language_scope"] = "speech_region"
            segment["speech_region_id"] = region_id
            segments.append(segment)
    return duration, segments, regions


def transcribe_audio(
    input_audio: Path,
    source_id: str | None = None,
    conversation_id: str | None = None,
    language: str | None = "vi",
    cache_dir: Path = DEFAULT_CACHE,
    cpu_threads: int = 2,
    offline: bool = False,
    *,
    video: bool = False,
) -> dict:
    if cpu_threads < 1:
        raise ValueError("CPU threads must be at least 1.")
    with input_audio.open("rb") as source:
        source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    resolved_source_id = source_id or f"sha256:{source_hash}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_dir / "hf-home"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

    # Import after configuring the local download cache. Model inference is local.
    from faster_whisper import WhisperModel
    from faster_whisper.tokenizer import _LANGUAGE_CODES
    from faster_whisper.utils import download_model

    requested_language = "auto" if language is None else language.strip().lower()
    detect_language = requested_language in ("auto", "mixed")
    if not detect_language and requested_language not in _LANGUAGE_CODES:
        raise ValueError(
            f"Unsupported language {requested_language!r}. "
            "Use a supported language code, auto, or mixed."
        )
    model_language = None if detect_language else requested_language
    language_mode = requested_language if detect_language else "fixed"

    started = time.perf_counter()
    ready_for_model = started
    source_type = "video" if video else "audio"
    audio_input = str(input_audio)
    if video:
        from video_audio import decode_video_audio

        audio_input, audio_stream_index, audio_start = decode_video_audio(input_audio, SAMPLE_RATE)
        ready_for_model = time.perf_counter()
    model_path = download_model(
        "small",
        cache_dir=str(cache_dir),
        revision=MODEL_REVISION,
        local_files_only=offline,
        use_auth_token=False,
    )
    model = WhisperModel(
        model_path,
        device="cpu",
        compute_type="int8",
        cpu_threads=cpu_threads,
        num_workers=1,
    )
    loaded = time.perf_counter()
    settings = {
        "language": model_language,
        "multilingual": False,
        "task": "transcribe",
        "beam_size": 5,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "vad_filter": False,
        "word_timestamps": False,
    }
    speech_regions = []
    if language_mode == "mixed":
        duration, segments, speech_regions = transcribe_mixed(
            model, audio_input, resolved_source_id, settings
        )
        detected_languages = list(dict.fromkeys(region["language"] for region in speech_regions))
        output_language = "und"
        if detected_languages:
            output_language = detected_languages[0] if len(detected_languages) == 1 else "mul"
        language_source = "detected_per_speech_region"
    else:
        raw_segments, info = model.transcribe(audio_input, **settings)
        output_language = info.language if detect_language else model_language
        duration = float(info.duration)
        segments = segment_records(raw_segments, resolved_source_id, duration)
        language_source = "detected_initial_window" if detect_language else "explicit"
    if video:
        duration += audio_start
        for interval in segments + speech_regions:
            interval["start_seconds"] = round(interval["start_seconds"] + audio_start, 3)
            interval["end_seconds"] = round(min(duration, interval["end_seconds"] + audio_start), 3)
    with input_audio.open("rb") as source:
        final_source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    if final_source_hash != source_hash:
        raise ValueError(f"The source {source_type} changed during transcription. Retry with a stable file.")
    finished = time.perf_counter()
    document = {
        "schema_version": 1,
        "source_id": resolved_source_id,
        "source_file": input_audio.name,
        "source_type": source_type,
        "source_sha256": source_hash,
        "duration_seconds": round(duration, 3),
        "language": output_language,
        "language_source": language_source,
        "language_mode": language_mode,
        "language_requested": requested_language,
        "variant": "asr",
        "review_status": "unreviewed",
        "status": "ok" if segments else "no_speech_detected",
        "processor": {
            "name": "faster-whisper",
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "device": "cpu",
            "compute_type": "int8",
            "cpu_threads": cpu_threads,
            "num_workers": 1,
            "settings": settings,
            "software_versions": {
                package: version(package)
                for package in (
                    "faster-whisper", "ctranslate2", "huggingface-hub",
                    "tokenizers", "av", "numpy", "onnxruntime",
                )
            },
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "model_download_and_load_seconds": round(loaded - ready_for_model, 3),
            "transcription_seconds": round(finished - loaded, 3),
            "total_seconds": round(finished - started, 3),
        },
        "segments": segments,
    }
    if video:
        document["audio_stream_index"] = audio_stream_index
        document["audio_start_seconds"] = round(audio_start, 3)
        document["runtime"]["video_decode_seconds"] = round(ready_for_model - started, 3)
    if conversation_id is not None:
        document["conversation_id"] = conversation_id
    if language_mode == "auto":
        document["initial_language_probability"] = float(info.language_probability)
    if language_mode == "mixed":
        document["languages_detected"] = detected_languages
        document["speech_regions"] = speech_regions
        document["processor"]["mixed_language_processing"] = {
            "strategy": "detect_language_per_speech_region",
            "vad_model": "silero_bundled_with_faster_whisper",
            "vad_settings": MIXED_VAD_SETTINGS.copy(),
            "sample_rate": SAMPLE_RATE,
        }
    return document


def write_transcript(document: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=output.parent,
            prefix=".audio-transcript-", suffix=".tmp", delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(document, temporary, ensure_ascii=False, allow_nan=False, indent=2)
            temporary.write("\n")
        temporary_path.replace(output)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_media", type=Path, help="Path to an audio file or a video with --video.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--video", action="store_true", help="Transcribe the first audio track of a video.")
    parser.add_argument("--source-id")
    parser.add_argument("--conversation-id")
    parser.add_argument(
        "--language",
        default="vi",
        help="vi (default), en, another supported code, auto, or mixed.",
    )
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--cpu-threads", type=int, default=2)
    parser.add_argument("--offline", action="store_true", help="Use only cached model files.")
    arguments = parser.parse_args()
    if arguments.input_media.resolve() == arguments.output.resolve():
        parser.error("The output must be a different file from the source recording.")
    try:
        document = transcribe_audio(
            arguments.input_media,
            arguments.source_id,
            arguments.conversation_id,
            arguments.language,
            arguments.cache_dir,
            arguments.cpu_threads,
            arguments.offline,
            video=arguments.video,
        )
        write_transcript(document, arguments.output)
    except Exception as error:
        print(f"Transcription failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(
        f"Saved {len(document['segments'])} segments from "
        f"{document['duration_seconds']} seconds to {arguments.output}. "
        "Review the words and timestamps against the recording."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
