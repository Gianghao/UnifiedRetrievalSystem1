"""Offline synthetic checks for Vietnamese settings and source-time provenance."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

from transcribe_audio import segment_records, transcribe_audio, write_transcript


class AudioTranscriptionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "sample.wav"
        with wave.open(str(self.source), "wb") as source:
            source.setnchannels(1)
            source.setsampwidth(2)
            source.setframerate(16000)
            source.writeframes(b"\x00\x00" * 32000)

    def test_installed_decoder_reads_real_wav_samples(self):
        from faster_whisper.audio import decode_audio

        samples = decode_audio(str(self.source), sampling_rate=16000)
        self.assertEqual(samples.shape, (32000,))
        self.assertEqual(str(samples.dtype), "float32")

    def test_vietnamese_transcription_preserves_source_and_diacritics(self):
        model = Mock()
        model.transcribe.return_value = (
            iter([SimpleNamespace(start=0.2, end=1.9, text=" Xin chào Việt Nam. ")]),
            SimpleNamespace(duration=2.0),
        )
        with (
            patch("faster_whisper.WhisperModel", return_value=model) as factory,
            patch("faster_whisper.utils.download_model", return_value="cached-model") as download,
        ):
            document = transcribe_audio(
                self.source,
                source_id="attachment-123",
                conversation_id="conversation-456",
                cache_dir=Path(self.directory.name) / "models",
                offline=True,
            )
        factory.assert_called_once_with(
            "cached-model", device="cpu", compute_type="int8", cpu_threads=2, num_workers=1
        )
        self.assertTrue(download.call_args.kwargs["local_files_only"])
        settings = model.transcribe.call_args.kwargs
        self.assertEqual(settings["language"], "vi")
        self.assertEqual(settings["task"], "transcribe")
        self.assertFalse(settings["vad_filter"])
        self.assertEqual(document["source_id"], "attachment-123")
        self.assertEqual(document["conversation_id"], "conversation-456")
        self.assertEqual(
            document["source_sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest()
        )
        self.assertEqual(document["review_status"], "unreviewed")
        segment = document["segments"][0]
        self.assertEqual(segment["text"], "Xin chào Việt Nam.")
        self.assertEqual(segment["start_seconds"], 0.2)
        self.assertEqual(segment["end_seconds"], 1.9)
        self.assertEqual(segment["source_id"], document["source_id"])
        output = self.source.with_suffix(".json")
        write_transcript(document, output)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), document)

    def test_invalid_timestamps_are_rejected(self):
        for start, end in ((-0.1, 1.0), (1.0, 0.5), (0.1, 3.0), (float("nan"), 1.0)):
            with self.subTest(start=start, end=end):
                with self.assertRaisesRegex(ValueError, "timestamps"):
                    segment_records(
                        [SimpleNamespace(start=start, end=end, text="Xin chào")], "source", 2.0
                    )

    def test_changing_audio_cannot_produce_stale_source_provenance(self):
        def change_source(*args, **kwargs):
            self.source.write_bytes(b"changed while the recognizer was running")
            return (
                iter([SimpleNamespace(start=0, end=1, text="Xin chào")]),
                SimpleNamespace(duration=2.0),
            )

        model = Mock()
        model.transcribe.side_effect = change_source
        with (
            patch("faster_whisper.WhisperModel", return_value=model),
            patch("faster_whisper.utils.download_model", return_value="cached-model"),
        ):
            with self.assertRaisesRegex(ValueError, "source audio changed"):
                transcribe_audio(self.source, cache_dir=Path(self.directory.name) / "models")

    def test_timestamp_rounding_is_bounded_by_actual_duration(self):
        records = segment_records(
            [SimpleNamespace(start=0.0, end=2.02, text="Xin chào")], "source", 2.0
        )
        self.assertEqual(records[0]["end_seconds"], 2.0)

    def test_empty_segments_are_explicitly_empty(self):
        self.assertEqual(segment_records([], "source", 2.0), [])
        self.assertEqual(
            segment_records([SimpleNamespace(start=0, end=1, text="  ")], "source", 2), []
        )

    def test_cli_missing_source_preserves_existing_output(self):
        output = self.source.with_suffix(".json")
        output.write_text("previous result", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable, str(Path(__file__).with_name("transcribe_audio.py")),
                str(self.source.with_name("missing.wav")), "--output", str(output), "--offline",
            ],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Transcription failed", result.stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "previous result")

    def test_cli_protects_original_recording(self):
        original = self.source.read_bytes()
        result = subprocess.run(
            [
                sys.executable, str(Path(__file__).with_name("transcribe_audio.py")),
                str(self.source), "--output", str(self.source), "--offline",
            ],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
