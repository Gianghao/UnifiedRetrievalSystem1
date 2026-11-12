"""Transcribe local audio into Vietnamese source-linked, timestamped segments."""

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


def transcribe_audio(
    input_audio: Path,
    source_id: str | None = None,
    conversation_id: str | None = None,
    language: str = "vi",
    cache_dir: Path = DEFAULT_CACHE,
    cpu_threads: int = 2,
    offline: bool = False,
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
    from faster_whisper.utils import download_model

    started = time.perf_counter()
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
        "language": language,
        "task": "transcribe",
        "beam_size": 5,
        "temperature": 0.0,
        "condition_on_previous_text": False,
        "vad_filter": False,
        "word_timestamps": False,
    }
    raw_segments, info = model.transcribe(str(input_audio), **settings)
    duration = float(info.duration)
    segments = segment_records(raw_segments, resolved_source_id, duration)
    with input_audio.open("rb") as source:
        final_source_hash = hashlib.file_digest(source, "sha256").hexdigest()
    if final_source_hash != source_hash:
        raise ValueError("The source audio changed during transcription. Retry with a stable file.")
    finished = time.perf_counter()
    document = {
        "schema_version": 1,
        "source_id": resolved_source_id,
        "source_file": input_audio.name,
        "source_type": "audio",
        "source_sha256": source_hash,
        "duration_seconds": round(duration, 3),
        "language": language,
        "language_source": "explicit",
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
                    "tokenizers", "av", "numpy",
                )
            },
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "model_download_and_load_seconds": round(loaded - started, 3),
            "transcription_seconds": round(finished - loaded, 3),
            "total_seconds": round(finished - started, 3),
        },
        "segments": segments,
    }
    if conversation_id is not None:
        document["conversation_id"] = conversation_id
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
    parser.add_argument("input_audio", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id")
    parser.add_argument("--conversation-id")
    parser.add_argument("--language", default="vi", help="Spoken-language code, default vi.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--cpu-threads", type=int, default=2)
    parser.add_argument("--offline", action="store_true", help="Use only cached model files.")
    arguments = parser.parse_args()
    if arguments.input_audio.resolve() == arguments.output.resolve():
        parser.error("The output must be a different file from the source audio.")
    try:
        document = transcribe_audio(
            arguments.input_audio,
            arguments.source_id,
            arguments.conversation_id,
            arguments.language,
            arguments.cache_dir,
            arguments.cpu_threads,
            arguments.offline,
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
