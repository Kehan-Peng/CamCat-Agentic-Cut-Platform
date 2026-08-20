from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from uuid import UUID

import pytest
from camcat.rendering.build import RenderBuildService
from camcat.rendering.ffmpeg_renderer import FFmpegRenderer
from camcat.rendering.fingerprint import fingerprint_media
from camcat.rendering.verification import VerificationLevel, verify_output
from camcat.timeline.compiler import TimelineCompiler
from camcat.timeline.schemas import RenderProfile

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
        reason="real FFmpeg and FFprobe are required",
    ),
]


def generate_video(path: Path, *, color: str, frequency: int) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color={color}:size=320x180:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
    )


def generate_audio(path: Path, *, frequency: int, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000:duration={duration}",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
    )


def test_two_clip_crossfade_subtitle_and_audio_render_is_verified(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    bgm = tmp_path / "bgm.m4a"
    sfx = tmp_path / "sfx.m4a"
    generate_video(first, color="red", frequency=440)
    generate_video(second, color="blue", frequency=660)
    generate_audio(bgm, frequency=220, duration=3)
    generate_audio(sfx, frequency=880, duration=0.4)

    sources = {
        "first": fingerprint_media(first, media_id="first", storage_key="test/first.mp4"),
        "second": fingerprint_media(second, media_id="second", storage_key="test/second.mp4"),
        "bgm": fingerprint_media(bgm, media_id="bgm", storage_key="test/bgm.m4a"),
        "sfx": fingerprint_media(sfx, media_id="sfx", storage_key="test/sfx.m4a"),
    }
    profile = RenderProfile(width=320, height=180, fps_num=30, default_dissolve_duration_ms=200)
    timeline = TimelineCompiler(profile).compile(
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        state_version=7,
        document={
            "clips": [
                {
                    "clip_id": "one",
                    "segment_id": "one",
                    "origin": "source",
                    "media_id": "first",
                    "source_start": 0.3,
                    "source_end": 1.3,
                    "transition": "dissolve",
                },
                {
                    "clip_id": "two",
                    "segment_id": "two",
                    "origin": "source",
                    "media_id": "second",
                    "source_start": 0.3,
                    "source_end": 1.3,
                    "transition": "cut",
                },
            ],
            "subtitles": [
                {
                    "subtitle_id": "subtitle",
                    "text": "CamCat compiled",
                    "clip_id": "one",
                    "source_id": "first",
                    "source_start": 0.4,
                    "source_end": 1.0,
                }
            ],
            "audio_plan": {
                "bgm": [
                    {
                        "cue_id": "music",
                        "media_id": "bgm",
                        "target_start": 0,
                        "target_duration": 1.8,
                        "volume": 0.08,
                        "fade_in_frames": 3,
                        "fade_out_frames": 3,
                    }
                ],
                "ambient": [],
                "sound_effects": [
                    {
                        "cue_id": "effect",
                        "media_id": "sfx",
                        "target_start": 0.6,
                        "target_duration": 0.3,
                        "volume": 0.25,
                    }
                ],
            },
        },
        sources=sources,
    )
    assert timeline.frame_count == 54
    build = RenderBuildService(renderer_version=FFmpegRenderer.VERSION).create(
        tmp_path / "build", timeline=timeline, profile=profile
    )
    output = tmp_path / "render.mp4"
    FFmpegRenderer().render(build, output)
    result = verify_output(build, output)

    assert result.status == VerificationLevel.EDITORIAL_QC_PENDING
    assert result.expected_frames == 54
    assert abs(result.frame_delta) <= 1
    assert result.full_decode_succeeds
    assert result.width == 320 and result.height == 180
    assert result.audio_stream_expected and result.audio_stream_actual
