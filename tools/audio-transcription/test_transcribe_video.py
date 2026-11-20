"""Check video decoding and timestamp provenance with synthetic media."""

from fractions import Fraction
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import av
import numpy as np

from transcribe_audio import SAMPLE_RATE, transcribe_audio


def make_video(path: Path, with_audio: bool) -> None:
    with av.open(str(path), "w") as container:
        video = container.add_stream("mpeg4", rate=10)
        video.width = video.height = 32
        video.pix_fmt = "yuv420p"
        if with_audio:
            audio = container.add_stream("pcm_s16le", rate=SAMPLE_RATE)
            audio.layout = "mono"
        for pts in range(20, 51):
            frame = av.VideoFrame(32, 32, "yuv420p")
            for plane in frame.planes:
                plane.update(bytes(plane.buffer_size))
            frame.pts = pts
            container.mux(video.encode(frame))
        container.mux(video.encode())
        if with_audio:
            # The container starts at 2 seconds. Audio starts at 3 with a 0.5-second gap.
            half_second = np.full((1, SAMPLE_RATE // 2), 16384, dtype=np.int16)
            for seconds in (3, 4):
                frame = av.AudioFrame.from_ndarray(half_second, format="s16", layout="mono")
                frame.sample_rate = SAMPLE_RATE
                frame.time_base = Fraction(1, SAMPLE_RATE)
                frame.pts = seconds * SAMPLE_RATE
                container.mux(audio.encode(frame))
            container.mux(audio.encode())


class VideoTranscriptionTests(unittest.TestCase):
    def setUp(self):
        working = tempfile.TemporaryDirectory()
        self.addCleanup(working.cleanup)
        self.directory = Path(working.name)
        self.source = self.directory / "sample.mkv"

    def test_delayed_audio_retains_video_identity_and_playback_timestamps(self):
        make_video(self.source, with_audio=True)
        model = Mock()
        model.transcribe.return_value = (
            [SimpleNamespace(start=1.1, end=1.4, text=" Xin chào. ")],
            SimpleNamespace(duration=1.5),
        )
        with (
            patch("faster_whisper.WhisperModel", return_value=model),
            patch("faster_whisper.utils.download_model", return_value="cached-model"),
        ):
            document = transcribe_audio(
                self.source, conversation_id="conversation", cache_dir=self.directory, video=True
            )

        samples = model.transcribe.call_args.args[0]
        np.testing.assert_array_equal(samples[:8000], np.full(8000, 0.5))
        np.testing.assert_array_equal(samples[8000:16000], np.zeros(8000))
        np.testing.assert_array_equal(samples[16000:], np.full(8000, 0.5))
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.assertEqual(document["source_file"], self.source.name)
        self.assertEqual(document["source_type"], "video")
        self.assertEqual(document["source_id"], f"sha256:{digest}")
        self.assertEqual(document["source_sha256"], digest)
        self.assertEqual(document["conversation_id"], "conversation")
        self.assertEqual(document["audio_stream_index"], 1)
        self.assertEqual(document["audio_start_seconds"], 1.0)
        self.assertEqual(document["duration_seconds"], 2.5)
        segment = document["segments"][0]
        self.assertEqual((segment["start_seconds"], segment["end_seconds"]), (2.1, 2.4))
        self.assertEqual(segment["text"], "Xin chào.")

    def test_mixed_language_video_offsets_speech_regions_as_well_as_segments(self):
        make_video(self.source, with_audio=True)
        model = Mock()
        model.transcribe.return_value = (
            [SimpleNamespace(start=0.1, end=0.4, text="Hello.")],
            SimpleNamespace(language="en", language_probability=0.9),
        )
        with (
            patch("faster_whisper.WhisperModel", return_value=model),
            patch("faster_whisper.utils.download_model", return_value="cached-model"),
            patch("faster_whisper.vad.get_speech_timestamps", return_value=[{"start": 16000, "end": 24000}]),
        ):
            document = transcribe_audio(
                self.source, language="mixed", cache_dir=self.directory, video=True
            )
        region = document["speech_regions"][0]
        segment = document["segments"][0]
        self.assertEqual((region["start_seconds"], region["end_seconds"]), (2.0, 2.5))
        self.assertEqual((segment["start_seconds"], segment["end_seconds"]), (2.1, 2.4))
        self.assertEqual(segment["speech_region_id"], region["region_id"])

    def test_video_without_audio_preserves_existing_json(self):
        make_video(self.source, with_audio=False)
        output = self.directory / "transcript.json"
        output.write_text("previous result", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable, str(Path(__file__).with_name("transcribe_audio.py")),
                str(self.source), "--video", "--offline", "--output", str(output),
            ],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("video has no audio track", result.stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "previous result")


if __name__ == "__main__":
    unittest.main()
