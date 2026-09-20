from __future__ import annotations

import math
import subprocess
from enum import StrEnum
from fractions import Fraction
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from camcat.rendering.build import RenderBuild, verify_render_build
from camcat.rendering.fingerprint import probe_json, sha256_file


class OutputVerificationError(ValueError):
    pass


class VerificationLevel(StrEnum):
    STRUCTURAL_VALID = "structural_valid"
    DECODE_VALID = "decode_valid"
    TIMELINE_VALID = "timeline_valid"
    EDITORIAL_QC_PENDING = "editorial_qc_pending"
    EDITORIAL_QC_PASSED = "editorial_qc_passed"


class OutputVerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: VerificationLevel
    output_sha256: str
    output_bytes: int
    width: int
    height: int
    fps: float
    duration_seconds: float
    expected_frames: int
    actual_frames: int
    frame_delta: int
    duration_delta_seconds: float
    audio_stream_expected: bool
    audio_stream_actual: bool
    full_decode_succeeds: bool


def verify_output(build: RenderBuild, output: Path) -> OutputVerificationResult:
    build = verify_render_build(build.root)
    output = output.resolve(strict=True)
    if not output.is_file() or output.stat().st_size <= 0:
        raise OutputVerificationError("render output is empty")
    payload = probe_json(output, count_frames=True)
    video = next(
        (item for item in payload.get("streams", []) if item.get("codec_type") == "video"), None
    )
    audio = next(
        (item for item in payload.get("streams", []) if item.get("codec_type") == "audio"), None
    )
    if video is None:
        raise OutputVerificationError("render output has no video stream")
    if (int(video.get("width", 0)), int(video.get("height", 0))) != (
        build.timeline.canvas.width,
        build.timeline.canvas.height,
    ):
        raise OutputVerificationError("render output dimensions differ from the render profile")
    fps = float(Fraction(str(video.get("avg_frame_rate") or video.get("r_frame_rate"))))
    expected_fps = build.timeline.canvas.fps_num / build.timeline.canvas.fps_den
    if not math.isclose(fps, expected_fps, abs_tol=0.001):
        raise OutputVerificationError("render output frame rate differs from the render profile")
    actual_frames = int(video.get("nb_read_frames") or video.get("nb_frames") or -1)
    frame_delta = actual_frames - build.timeline.frame_count
    if frame_delta != 0:
        raise OutputVerificationError(
            "render output frame count mismatch: "
            f"expected {build.timeline.frame_count}, got {actual_frames}"
        )
    duration = float(payload.get("format", {}).get("duration") or video.get("duration") or 0)
    expected_duration = build.timeline.duration_us / 1_000_000
    duration_delta = duration - expected_duration
    if abs(duration_delta) > max(
        0.05, build.timeline.canvas.fps_den / build.timeline.canvas.fps_num
    ):
        raise OutputVerificationError("render output duration differs from compiled timeline")
    # The render profile always produces an audio program. Sources without dialogue receive an
    # explicit silent bed, so a missing output audio stream is still a contract violation.
    audio_expected = True
    if audio_expected and audio is None:
        raise OutputVerificationError("render output is missing its expected audio stream")
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(output), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if decoded.returncode != 0:
        raise OutputVerificationError(f"render output full decode failed: {decoded.stderr[-2000:]}")
    return OutputVerificationResult(
        status=VerificationLevel.EDITORIAL_QC_PENDING,
        output_sha256=sha256_file(output),
        output_bytes=output.stat().st_size,
        width=int(video["width"]),
        height=int(video["height"]),
        fps=fps,
        duration_seconds=duration,
        expected_frames=build.timeline.frame_count,
        actual_frames=actual_frames,
        frame_delta=frame_delta,
        duration_delta_seconds=round(duration_delta, 6),
        audio_stream_expected=audio_expected,
        audio_stream_actual=audio is not None,
        full_decode_succeeds=True,
    )
