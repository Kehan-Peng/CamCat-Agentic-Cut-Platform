from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from camcat.rendering.build import RenderBuild, verify_render_build
from camcat.rendering.fingerprint import sha256_file
from camcat.timeline.schemas import CompiledAudioCue, CompiledTimeline
from camcat.timeline.validator import canonical_json, content_hash


class JianyingAdapterError(RuntimeError):
    pass


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class JianyingCanvas(_StrictModel):
    width: int = Field(ge=16, le=8192)
    height: int = Field(ge=16, le=8192)
    fps: Literal[24, 25, 30, 50, 60]


class JianyingTransition(_StrictModel):
    name: Literal["dissolve"] = "dissolve"
    duration_us: int = Field(gt=0)
    edge_policy: Literal["require-handles"] = "require-handles"


class JianyingKeyframe(_StrictModel):
    at_us: int = Field(ge=0)
    value: float = Field(ge=0, le=4)


class JianyingVideoSegment(_StrictModel):
    source: str
    start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    speed: float = Field(ge=0.1, le=8)
    volume: float = Field(default=1, ge=0, le=4)
    transition_out: JianyingTransition | None = None


class JianyingAudioSegment(_StrictModel):
    source: str
    start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    speed: Literal[1] = 1
    volume: float | None = Field(default=None, ge=0, le=4)
    keyframes: dict[Literal["volume"], list[JianyingKeyframe]] | None = None

    @model_validator(mode="after")
    def volume_contract(self) -> JianyingAudioSegment:
        if (self.volume is None) == (self.keyframes is None):
            raise ValueError("audio segment needs either static volume or volume keyframes")
        return self


class JianyingTextSegment(_StrictModel):
    text: str = Field(min_length=1)
    start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)
    size: float = Field(default=6, ge=1, le=100)
    x: float = Field(default=0, ge=-5, le=5)
    y: float = Field(default=-0.78, ge=-5, le=5)
    color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    border_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    border_width: float = Field(default=0.05, ge=0, le=1)


class JianyingVideoTrack(_StrictModel):
    type: Literal["video"] = "video"
    name: str = "CamCat 主视频"
    segments: list[JianyingVideoSegment] = Field(min_length=1)


class JianyingAudioTrack(_StrictModel):
    type: Literal["audio"] = "audio"
    name: str
    segments: list[JianyingAudioSegment] = Field(min_length=1)


class JianyingTextTrack(_StrictModel):
    type: Literal["text"] = "text"
    name: str = "CamCat 字幕"
    segments: list[JianyingTextSegment] = Field(min_length=1)


class JianyingDraftPlan(_StrictModel):
    schema_name: Literal["jy14-headless-plan/v1"] = Field(
        default="jy14-headless-plan/v1", alias="schema"
    )
    name: str = Field(min_length=1, max_length=100)
    canvas: JianyingCanvas
    tracks: list[JianyingVideoTrack | JianyingAudioTrack | JianyingTextTrack]

    @model_validator(mode="after")
    def valid_name_and_tracks(self) -> JianyingDraftPlan:
        if self.name != self.name.strip() or any(
            item in self.name for item in ("/", "\\", "\x00", "\n", "\r")
        ):
            raise ValueError("draft name must be one visible directory component")
        if not self.tracks or not isinstance(self.tracks[0], JianyingVideoTrack):
            raise ValueError("draft plan must start with its main video track")
        return self


class JianyingDraftResult(_StrictModel):
    adapter: Literal["camcat-jianying-adapter/v1"] = "camcat-jianying-adapter/v1"
    root: Path
    draft: Path
    plan: Path
    manifest: Path
    compiled_timeline_hash: str
    render_build_hash: str
    native_build_hash: str
    native_ui_acceptance: Literal["pending"] = "pending"


class JianyingRendererAdapter:
    """Optional local adapter that never publishes or opens the native editor automatically."""

    VERSION = "camcat-jianying-adapter/v1"

    def __init__(self, command: tuple[str, ...] | list[str]) -> None:
        if not command or any(not str(item).strip() for item in command):
            raise ValueError("adapter command must be a nonempty argument vector")
        self.command = tuple(str(item) for item in command)

    def compile_plan(self, build: RenderBuild, *, name: str) -> JianyingDraftPlan:
        build = verify_render_build(build.root)
        timeline = build.timeline
        if timeline.fps_den != 1 or timeline.fps_num not in {24, 25, 30, 50, 60}:
            raise JianyingAdapterError("native draft adapter requires an integer supported FPS")
        fps = timeline.fps_num
        sources = {item.media_id: item for item in timeline.source_manifest}
        video_segments: list[JianyingVideoSegment] = []
        cursor_frames = 0
        for segment in timeline.video_tracks[0].segments:
            incoming_frames = segment.transition_in.duration_frames
            native_frames = segment.target_duration_frames - incoming_frames
            if native_frames <= 0:
                raise JianyingAdapterError("transition consumes the native video segment")
            start_us, duration_us = _frame_range_us(cursor_frames, native_frames, fps)
            source_duration_us = _source_duration_us(duration_us, speed=segment.speed)
            source_start_us = (
                segment.source_start_us + segment.source_duration_us - source_duration_us
            )
            transition = None
            if segment.transition_out.type == "dissolve":
                transition_frames = segment.transition_out.duration_frames
                if transition_frames < 2 or transition_frames % 2:
                    raise JianyingAdapterError(
                        "native dissolve requires an even number of at least two frames"
                    )
                transition = JianyingTransition(duration_us=_frames_to_us(transition_frames, fps))
            video_segments.append(
                JianyingVideoSegment(
                    source=sources[segment.source_id].local_path,
                    start_us=start_us,
                    duration_us=duration_us,
                    source_start_us=source_start_us,
                    source_duration_us=source_duration_us,
                    speed=segment.speed,
                    transition_out=transition,
                )
            )
            cursor_frames += native_frames
        if cursor_frames != timeline.frame_count:
            raise JianyingAdapterError("native plan duration differs from compiled frame count")

        tracks: list[JianyingVideoTrack | JianyingAudioTrack | JianyingTextTrack] = [
            JianyingVideoTrack(segments=video_segments)
        ]
        if timeline.subtitles:
            tracks.append(
                JianyingTextTrack(
                    segments=[
                        JianyingTextSegment(
                            text=item.text,
                            start_us=_frames_to_us(item.target_start_frame, fps),
                            duration_us=(
                                _frames_to_us(item.target_end_frame, fps)
                                - _frames_to_us(item.target_start_frame, fps)
                            ),
                            **_subtitle_style(item.style),
                        )
                        for item in timeline.subtitles
                    ]
                )
            )
        tracks.extend(_audio_tracks(timeline))
        plan = JianyingDraftPlan(
            name=name,
            canvas=JianyingCanvas(
                width=timeline.width,
                height=timeline.height,
                fps=cast(Literal[24, 25, 30, 50, 60], fps),
            ),
            tracks=tracks,
        )
        verify_jianying_plan(plan, timeline)
        return plan

    def build_editable_draft(
        self,
        build: RenderBuild,
        output_root: Path,
        *,
        name: str,
    ) -> JianyingDraftResult:
        build = verify_render_build(build.root)
        plan = self.compile_plan(build, name=name)
        self._run("doctor")
        output_root = output_root.resolve()
        output_root.mkdir(parents=True, mode=0o700, exist_ok=False)
        plan_path = output_root / "jianying-plan.json"
        plan_path.write_bytes(
            canonical_json(plan.model_dump(mode="json", by_alias=True, exclude_none=True))
        )
        native_build = output_root / "native-build"
        build_result = self._run("build", "--plan", str(plan_path), "--out", str(native_build))
        if build_result.get("status") != "built" or build_result.get("live_written") is not False:
            raise JianyingAdapterError("native builder returned an invalid build result")
        report_path = output_root / "verify-report.json"
        verify_result = self._run(
            "verify-build",
            "--build",
            str(native_build),
            "--report",
            str(report_path),
        )
        if verify_result.get("status") != "verified" or not report_path.is_file():
            raise JianyingAdapterError("native draft build verification failed")
        required = (
            native_build / "build.json",
            native_build / "draft" / "draft_info.json",
            native_build / "draft" / "draft_meta_info.json",
        )
        if any(not item.is_file() for item in required):
            raise JianyingAdapterError("native draft build is incomplete")
        files = _files_manifest(native_build)
        native_hash = content_hash(files)
        manifest_path = output_root / "adapter-manifest.json"
        manifest_path.write_bytes(
            canonical_json(
                {
                    "schema": self.VERSION,
                    "compiled_timeline_hash": build.timeline.compiled_hash,
                    "render_build_hash": build.manifest.build_hash,
                    "plan_sha256": sha256_file(plan_path),
                    "native_build_hash": native_hash,
                    "native_files": files,
                    "native_ui_acceptance": "pending",
                    "published": False,
                }
            )
        )
        return JianyingDraftResult(
            root=output_root,
            draft=native_build / "draft",
            plan=plan_path,
            manifest=manifest_path,
            compiled_timeline_hash=build.timeline.compiled_hash,
            render_build_hash=build.manifest.build_hash,
            native_build_hash=native_hash,
        )

    def _run(self, *args: str) -> dict[str, Any]:
        result = subprocess.run([*self.command, *args], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise JianyingAdapterError(
                f"native draft command failed ({args[0]}): {result.stderr[-2000:]}"
            )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise JianyingAdapterError("native draft command returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise JianyingAdapterError("native draft command returned a non-object result")
        return payload


def _audio_tracks(timeline: CompiledTimeline) -> list[JianyingAudioTrack]:
    sources = {item.media_id: item for item in timeline.source_manifest}
    tracks: list[JianyingAudioTrack] = []
    for compiled_track in timeline.audio_tracks:
        if compiled_track.kind == "dialogue":
            continue
        lanes: list[list[JianyingAudioSegment]] = []
        for cue in sorted(
            compiled_track.cues, key=lambda item: (item.target_start_frame, item.cue_id)
        ):
            source = sources[cue.source_id]
            if source.video_codec:
                raise JianyingAdapterError(
                    f"native audio track requires an audio-only source: {cue.source_id}"
                )
            segments = _audio_cue_segments(timeline, cue)
            cue_start = segments[0].start_us
            lane = next(
                (
                    items
                    for items in lanes
                    if items[-1].start_us + items[-1].duration_us <= cue_start
                ),
                None,
            )
            if lane is None:
                lane = []
                lanes.append(lane)
            lane.extend(segments)
        for index, lane in enumerate(lanes, start=1):
            tracks.append(
                JianyingAudioTrack(
                    name=f"CamCat {compiled_track.kind.upper()} {index}", segments=lane
                )
            )
    return tracks


def verify_jianying_plan(plan: JianyingDraftPlan, timeline: CompiledTimeline) -> None:
    main = plan.tracks[0]
    if not isinstance(main, JianyingVideoTrack):
        raise JianyingAdapterError("native plan has no main video track")
    cursor = 0
    for index, segment in enumerate(main.segments):
        if segment.start_us != cursor:
            raise JianyingAdapterError("native main video track is not continuous")
        if abs(segment.source_duration_us / segment.speed - segment.duration_us) > 2:
            raise JianyingAdapterError("native source and target durations disagree")
        if segment.transition_out is not None:
            if index == len(main.segments) - 1:
                raise JianyingAdapterError("native final segment has an outgoing transition")
            if segment.transition_out.duration_us > min(
                segment.duration_us, main.segments[index + 1].duration_us
            ):
                raise JianyingAdapterError("native transition exceeds an adjacent segment")
        cursor += segment.duration_us
    if cursor != timeline.duration_us:
        raise JianyingAdapterError("native plan duration differs from compiled timeline")
    for track in plan.tracks[1:]:
        previous_end = 0
        for overlay_segment in track.segments:
            if overlay_segment.start_us < previous_end:
                raise JianyingAdapterError("native overlay track contains an overlap")
            end = overlay_segment.start_us + overlay_segment.duration_us
            if end > cursor:
                raise JianyingAdapterError("native overlay leaves the compiled timeline")
            previous_end = end


def _audio_cue_segments(
    timeline: CompiledTimeline, cue: CompiledAudioCue
) -> list[JianyingAudioSegment]:
    fps = timeline.fps_num
    source = next(item for item in timeline.source_manifest if item.media_id == cue.source_id)
    remaining = cue.target_duration_frames
    target_frame = cue.target_start_frame
    cue_offset = 0
    source_start_us = cue.source_start_us
    result: list[JianyingAudioSegment] = []
    while remaining:
        available_us = source.duration_us - source_start_us
        available_frames = available_us * fps // 1_000_000
        if available_frames <= 0:
            raise JianyingAdapterError("audio cue has no frame-aligned source samples")
        frames = min(remaining, available_frames)
        start_us, duration_us = _frame_range_us(target_frame, frames, fps)
        keyframes = _volume_keyframes(cue, cue_offset, frames, duration_us, fps)
        if keyframes is not None and source_start_us != 0:
            raise JianyingAdapterError(
                "native volume fades require an audio cue starting at source zero"
            )
        result.append(
            JianyingAudioSegment(
                source=source.local_path,
                start_us=start_us,
                duration_us=duration_us,
                source_start_us=source_start_us,
                source_duration_us=duration_us,
                volume=None if keyframes else cue.volume,
                keyframes={"volume": keyframes} if keyframes else None,
            )
        )
        remaining -= frames
        target_frame += frames
        cue_offset += frames
        if remaining and not cue.loop:
            raise JianyingAdapterError("audio cue exceeds its source without loop intent")
        source_start_us = 0
    return result


def _volume_keyframes(
    cue: CompiledAudioCue,
    piece_start: int,
    piece_frames: int,
    piece_duration_us: int,
    fps: int,
) -> list[JianyingKeyframe] | None:
    if not cue.fade_in_frames and not cue.fade_out_frames:
        return None
    piece_end = piece_start + piece_frames
    boundaries = {piece_start, piece_end}
    if piece_start < cue.fade_in_frames < piece_end:
        boundaries.add(cue.fade_in_frames)
    fade_out_start = cue.target_duration_frames - cue.fade_out_frames
    if piece_start < fade_out_start < piece_end:
        boundaries.add(fade_out_start)

    def volume_at(frame: int) -> float:
        multiplier = 1.0
        if cue.fade_in_frames:
            multiplier = min(multiplier, frame / cue.fade_in_frames)
        if cue.fade_out_frames:
            multiplier = min(
                multiplier,
                max(0.0, (cue.target_duration_frames - frame) / cue.fade_out_frames),
            )
        return cue.volume * multiplier

    result = []
    for frame in sorted(boundaries):
        at_us = piece_duration_us if frame == piece_end else _frames_to_us(frame - piece_start, fps)
        result.append(JianyingKeyframe(at_us=at_us, value=volume_at(frame)))
    return result


def _subtitle_style(value: dict[str, Any] | str) -> dict[str, Any]:
    if value == "default":
        return {}
    if not isinstance(value, dict):
        raise JianyingAdapterError("unsupported native subtitle style")
    allowed = {"size", "x", "y", "color", "border_color", "border_width"}
    if set(value) - allowed:
        raise JianyingAdapterError("subtitle style contains unsupported native fields")
    return dict(value)


def _source_duration_us(target_duration_us: int, *, speed: float) -> int:
    ratio = Fraction(str(speed))
    return _round_ratio(target_duration_us * ratio.numerator, ratio.denominator)


def _frames_to_us(frames: int, fps: int) -> int:
    return _round_ratio(frames * 1_000_000, fps)


def _frame_range_us(start_frame: int, duration_frames: int, fps: int) -> tuple[int, int]:
    start_us = _frames_to_us(start_frame, fps)
    return start_us, _frames_to_us(start_frame + duration_frames, fps) - start_us


def _round_ratio(numerator: int, denominator: int) -> int:
    return (2 * numerator + denominator) // (2 * denominator)


def _files_manifest(root: Path) -> dict[str, dict[str, int | str]]:
    files: dict[str, dict[str, int | str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise JianyingAdapterError("native draft build cannot contain symlinks")
        if path.is_file():
            files[str(path.relative_to(root))] = {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
    return files
