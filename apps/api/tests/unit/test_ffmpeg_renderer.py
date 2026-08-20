from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import camcat.rendering.ffmpeg_renderer as renderer_module
import camcat.rendering.fingerprint as fingerprint_module
import pytest
from camcat.rendering.build import RenderBuildService
from camcat.rendering.ffmpeg_renderer import FFmpegRenderer
from camcat.timeline.compiler import TimelineCompiler
from camcat.timeline.schemas import MediaFingerprint, RenderProfile


def test_renderer_consumes_profile_without_hidden_fps_or_audio_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    monkeypatch.setattr(
        fingerprint_module,
        "probe_json",
        lambda _path: {"format": {"duration": "2.0"}},
    )
    fingerprint = MediaFingerprint(
        media_id="source",
        storage_key="test/source.mp4",
        local_path=str(source),
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        file_size=source.stat().st_size,
        duration_us=2_000_000,
        width=640,
        height=360,
        video_codec="h264",
        audio_codec="aac",
    )
    profile = RenderProfile(
        width=640,
        height=360,
        fps_num=25,
        audio_channels=1,
        color_contrast=1.1,
        color_saturation=0.9,
        color_gamma=1.2,
        loudness_target_lufs=-16,
    )
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
                    "source_start": 0,
                    "source_end": 1,
                    "transition": "cut",
                }
            ],
            "subtitles": [],
            "audio_plan": {"bgm": [], "ambient": [], "sound_effects": []},
        },
        sources={"source": fingerprint},
    )
    build = RenderBuildService(renderer_version=FFmpegRenderer.VERSION).create(
        tmp_path / "build", timeline=timeline, profile=profile
    )
    captured: list[str] = []

    def run(args, **_kwargs):
        captured.extend(args)
        Path(args[-1]).write_bytes(b"encoded")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(renderer_module.subprocess, "run", run)
    FFmpegRenderer().render(build, tmp_path / "output.mp4")

    graph = captured[captured.index("-filter_complex") + 1]
    assert "fps=25/1" in graph
    assert "fps=30" not in graph
    assert "eq=contrast=1.1:saturation=0.9:gamma=1.2" in graph
    assert "aformat=channel_layouts=mono" in graph
    assert "loudnorm=I=-16" in graph
