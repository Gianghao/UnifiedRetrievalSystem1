"""Synthetic checks for language modes, decoding, and source-time provenance."""

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
        self.assertFalse(settings["multilingual"])
        self.assertFalse(settings["vad_filter"])
        self.assertEqual(document["source_id"], "attachment-123")
        self.assertEqual(document["conversation_id"], "conversation-456")
        self.assertEqual(
            document["source_sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest()
        )
        self.assertEqual(document["review_status"], "unreviewed")
        self.assertEqual(document["language_mode"], "fixed")
        self.assertEqual(document["language_requested"], "vi")
        self.assertEqual(document["language_source"], "explicit")
        self.assertNotIn("initial_language_probability", document)
        segment = document["segments"][0]
        self.assertEqual(segment["text"], "Xin chào Việt Nam.")
        self.assertEqual(segment["start_seconds"], 0.2)
        self.assertEqual(segment["end_seconds"], 1.9)
        self.assertEqual(segment["source_id"], document["source_id"])
        output = self.source.with_suffix(".json")
        write_transcript(document, output)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), document)

    def test_english_and_auto_modes_record_their_language_scope(self):
        cases = (
            ("en", "en", False, "fixed"),
            (" EN ", "en", False, "fixed"),
            ("auto", None, False, "auto"),
            (None, None, False, "auto"),
        )
        for requested, expected_language, multilingual, mode in cases:
            with self.subTest(language=requested):
                model = Mock()
                model.transcribe.return_value = (
                    iter([SimpleNamespace(start=0.2, end=1.9, text="Please call Alex.")]),
                    SimpleNamespace(duration=2.0, language="en", language_probability=0.92),
                )
                with (
                    patch("faster_whisper.WhisperModel", return_value=model),
                    patch("faster_whisper.utils.download_model", return_value="cached-model"),
                ):
                    document = transcribe_audio(
                        self.source,
                        language=requested,
                        cache_dir=Path(self.directory.name) / "models",
                        offline=True,
                    )
                settings = model.transcribe.call_args.kwargs
                self.assertEqual(settings["language"], expected_language)
                self.assertEqual(settings["multilingual"], multilingual)
                self.assertEqual(settings["task"], "transcribe")
                self.assertEqual(document["language_mode"], mode)
                self.assertEqual(document["language"], "en")
                if mode == "fixed":
                    self.assertEqual(document["language_source"], "explicit")
                    self.assertNotIn("initial_language_probability", document)
                else:
                    self.assertEqual(document["language_source"], "detected_initial_window")
                    self.assertEqual(document["initial_language_probability"], 0.92)
                # The SDK provides an initial language, not segment-level language labels.
                self.assertNotIn("language", document["segments"][0])

    def test_mixed_languages_restore_offsets_and_keep_unique_segment_ids(self):
        import numpy as np

        model = Mock()
        model.transcribe.side_effect = [
            (
                iter([SimpleNamespace(start=0.1, end=0.6, text="Xin chào.")]),
                SimpleNamespace(language="vi", language_probability=0.9),
            ),
            (
                iter([SimpleNamespace(start=0.05, end=0.55, text="Hello Alex.")]),
                SimpleNamespace(language="en", language_probability=0.95),
            ),
        ]
        ranges = [{"start": 1600, "end": 14400}, {"start": 17600, "end": 30400}]
        with (
            patch("faster_whisper.WhisperModel", return_value=model),
            patch("faster_whisper.utils.download_model", return_value="cached-model"),
            patch("faster_whisper.audio.decode_audio", return_value=np.zeros(32000, dtype=np.float32)),
            patch("faster_whisper.vad.get_speech_timestamps", return_value=ranges),
        ):
            document = transcribe_audio(
                self.source,
                source_id="attachment-123",
                language="mixed",
                cache_dir=Path(self.directory.name) / "models",
                offline=True,
            )
        self.assertEqual(document["duration_seconds"], 2.0)
        self.assertEqual(document["language_mode"], "mixed")
        self.assertEqual(document["language"], "mul")
        self.assertEqual(document["languages_detected"], ["vi", "en"])
        self.assertEqual(document["language_source"], "detected_per_speech_region")
        self.assertNotIn("initial_language_probability", document)
        first, second = document["segments"]
        self.assertEqual((first["start_seconds"], first["end_seconds"]), (0.2, 0.7))
        self.assertEqual((second["start_seconds"], second["end_seconds"]), (1.15, 1.65))
        self.assertNotEqual(first["segment_id"], second["segment_id"])
        self.assertEqual([first["language"], second["language"]], ["vi", "en"])
        self.assertEqual(first["language_scope"], "speech_region")
        self.assertEqual(model.transcribe.call_count, 2)
        for call in model.transcribe.call_args_list:
            self.assertIsNone(call.kwargs["language"])
            self.assertFalse(call.kwargs["multilingual"])
            self.assertFalse(call.kwargs["vad_filter"])

    def test_silent_mixed_audio_produces_no_invented_language_or_text(self):
        model = Mock()
        with (
            patch("faster_whisper.WhisperModel", return_value=model),
            patch("faster_whisper.utils.download_model", return_value="cached-model"),
        ):
            document = transcribe_audio(
                self.source, language="mixed", cache_dir=Path(self.directory.name) / "models"
            )
        self.assertEqual(document["language"], "und")
        self.assertEqual(document["languages_detected"], [])
        self.assertEqual(document["speech_regions"], [])
        self.assertEqual(document["segments"], [])
        self.assertEqual(document["status"], "no_speech_detected")
        model.transcribe.assert_not_called()

    def test_other_supported_language_codes_keep_working(self):
        model = Mock()
        model.transcribe.return_value = (
            iter([SimpleNamespace(start=0, end=1, text="Bonjour.")]),
            SimpleNamespace(duration=2.0),
        )
        with (
            patch("faster_whisper.WhisperModel", return_value=model),
            patch("faster_whisper.utils.download_model", return_value="cached-model"),
        ):
            document = transcribe_audio(
                self.source, language="fr", cache_dir=Path(self.directory.name) / "models"
            )
        self.assertEqual(model.transcribe.call_args.kwargs["language"], "fr")
        self.assertEqual(document["language"], "fr")

    def test_invalid_language_is_rejected_before_model_download(self):
        with patch("faster_whisper.utils.download_model") as download:
            with self.assertRaisesRegex(ValueError, "Unsupported language"):
                transcribe_audio(
                    self.source,
                    language="invalid-language",
                    cache_dir=Path(self.directory.name) / "models",
                )
        download.assert_not_called()

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
