from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from uuid import UUID

import pytest
from camcat.rendering.build import RenderBuildService
from camcat.rendering.fingerprint import fingerprint_media
from camcat.rendering.jianying_adapter import JianyingRendererAdapter
from camcat.timeline.compiler import TimelineCompiler
from camcat.timeline.schemas import RenderProfile

COMMAND_JSON = os.getenv("CAMCAT_JIANYING_COMMAND_JSON")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(platform.system() != "Darwin", reason="local editable draft requires macOS"),
    pytest.mark.skipif(not COMMAND_JSON, reason="CAMCAT_JIANYING_COMMAND_JSON is not configured"),
    pytest.mark.skipif(
        shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
        reason="real FFmpeg and FFprobe are required",
    ),
]


def test_real_local_adapter_builds_and_verifies_editable_draft(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source),
        ],
        check=True,
    )
    fingerprint = fingerprint_media(source, media_id="source", storage_key="test/source.mp4")
    profile = RenderProfile(width=320, height=180, fps_num=30)
    timeline = TimelineCompiler(profile).compile(
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        state_version=1,
        document={
            "clips": [
                {
                    "clip_id": "clip",
                    "segment_id": "segment",
                    "origin": "source",
                    "media_id": "source",
                    "source_start": 0.2,
                    "source_end": 1.2,
                    "transition": "cut",
                }
            ],
            "subtitles": [
                {
                    "subtitle_id": "subtitle",
                    "text": "CamCat editable draft",
                    "clip_id": "clip",
                    "source_id": "source",
                    "source_start": 0.3,
                    "source_end": 0.9,
                }
            ],
            "audio_plan": {"bgm": [], "ambient": [], "sound_effects": []},
        },
        sources={"source": fingerprint},
    )
    build = RenderBuildService(renderer_version="integration/v1").create(
        tmp_path / "build", timeline=timeline, profile=profile
    )
    command = json.loads(str(COMMAND_JSON))
    result = JianyingRendererAdapter(command).build_editable_draft(
        build, tmp_path / "editable", name="CamCat Integration Draft"
    )

    assert result.draft.is_dir()
    assert result.manifest.is_file()
    assert result.native_ui_acceptance == "pending"
