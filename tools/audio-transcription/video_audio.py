"""Decode video speech input while retaining its position on the playback timeline."""

from itertools import chain
from pathlib import Path

import av
import numpy as np


def decode_video_audio(input_video: Path, sample_rate: int) -> tuple[np.ndarray, int, float]:
    """Return mono samples, the audio stream index, and the first sample's time."""
    with av.open(str(input_video), mode="r", metadata_errors="ignore") as container:
        if not any(
            not (stream.disposition & av.stream.Disposition.attached_pic)
            for stream in container.streams.video
        ):
            raise ValueError("The source must contain a video stream.")
        if not container.streams.audio:
            raise ValueError("The video has no audio track to transcribe.")

        stream = container.streams.audio[0]
        origin = (container.start_time or 0) / av.time_base
        resampler = av.AudioResampler(format="flt", layout="mono", rate=sample_rate)
        chunks = []
        first_sample = None
        next_sample = 0
        timestamp_tolerance = 1

        for frame in chain(container.decode(stream), (None,)):
            if frame is not None and frame.time_base is not None:
                # Some containers only store timestamps to the nearest millisecond.
                timestamp_tolerance = max(1, round(frame.time_base * sample_rate))
            for converted in resampler.resample(frame):
                start = next_sample
                if converted.pts is not None and converted.time_base is not None:
                    start = round((converted.pts * converted.time_base - origin) * sample_rate)
                samples = converted.to_ndarray().reshape(-1)
                if first_sample is None:
                    next_sample = max(0, start)
                elif abs(start - next_sample) <= timestamp_tolerance:
                    start = next_sample
                if start > next_sample:
                    chunks.append(np.zeros(start - next_sample, dtype=np.float32))
                    next_sample = start
                samples = samples[next_sample - start:]
                if samples.size:
                    if first_sample is None:
                        first_sample = next_sample
                    chunks.append(samples)
                    next_sample += samples.size

        if first_sample is None:
            raise ValueError("The selected video audio track has no playable samples.")
        return np.concatenate(chunks), stream.index, first_sample / sample_rate
