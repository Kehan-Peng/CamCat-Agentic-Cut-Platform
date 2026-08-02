from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from camcat.media.ffmpeg import concat_clips, normalize_clip, probe, write_srt

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("ffmpeg") is None, reason="FFmpeg is available in the API image"
    ),
]


def test_real_ffmpeg_render_has_video_audio_and_burned_subtitles(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    normalized = tmp_path / "normalized.mp4"
    normalize_clip(source, normalized, width=360, height=640)
    subtitles = tmp_path / "subtitles.srt"
    write_srt([{"text": "CamCat 字幕", "start": 0.1, "end": 1.8}], subtitles)
    supplements = []
    for index, frequency in enumerate((220, 330, 880)):
        audio = tmp_path / f"supplement-{index}.mp3"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={frequency}:duration=2",
                str(audio),
            ],
            check=True,
            capture_output=True,
        )
        supplements.append(audio)
    output = tmp_path / "render.mp4"
    concat_clips(
        [normalized],
        output,
        subtitles=subtitles,
        background_music=supplements[0],
        ambient_audio=supplements[1],
        sound_effect=supplements[2],
    )
    metadata = probe(output)
    assert 1.8 <= metadata.duration <= 2.2
    assert (metadata.width, metadata.height) == (360, 640)
    assert metadata.has_audio
