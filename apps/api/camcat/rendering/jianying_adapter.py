from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from camcat.rendering.build import RenderBuild, verify_materialized_sources, verify_render_build
from camcat.rendering.fingerprint import sha256_file
from camcat.rendering.materialization import MaterializedSources
from camcat.timeline.frames import frame_to_us
from camcat.timeline.schemas import CompiledTimelineV2
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


class JianyingVideoSegment(_StrictModel):
    source: str
    start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    speed: float = Field(ge=0.1, le=8)
    x: float = 0
    y: float = 0
    scale: float = Field(default=1, gt=0)
    rotation: float = 0
    opacity: float = Field(default=1, ge=0, le=1)
    transition_out: JianyingTransition | None = None


class JianyingAudioSegment(_StrictModel):
    source: str
    start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    speed: Literal[1] = 1
    volume: float = Field(default=1, ge=0, le=4)


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
    name: str
    segments: list[JianyingVideoSegment] = Field(min_length=1)


class JianyingAudioTrack(_StrictModel):
    type: Literal["audio"] = "audio"
    name: str
    segments: list[JianyingAudioSegment] = Field(min_length=1)


class JianyingTextTrack(_StrictModel):
    type: Literal["text"] = "text"
    name: str
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
            raise ValueError("draft plan must start with its primary video track")
        return self


class JianyingDraftResult(_StrictModel):
    adapter: Literal["camcat-jianying-adapter/v2"] = "camcat-jianying-adapter/v2"
    root: Path
    draft: Path
    plan: Path
    manifest: Path
    compiled_timeline_hash: str
    render_build_hash: str
    native_build_hash: str
    native_ui_acceptance: Literal["pending"] = "pending"


class JianyingRendererAdapter:
    """Build-only native adapter. It consumes CompiledTimeline V2 and never publishes."""

    VERSION = "camcat-jianying-adapter/v2"

    def __init__(self, command: tuple[str, ...] | list[str]) -> None:
        if not command or any(not str(item).strip() for item in command):
            raise ValueError("adapter command must be a nonempty argument vector")
        self.command = tuple(str(item) for item in command)

    def compile_plan(
        self,
        build: RenderBuild,
        sources: MaterializedSources,
        *,
        name: str,
    ) -> JianyingDraftPlan:
        build = verify_render_build(build.root)
        verify_materialized_sources(build, sources)
        timeline = build.timeline
        if timeline.canvas.fps_den != 1 or timeline.canvas.fps_num not in {24, 25, 30, 50, 60}:
            raise JianyingAdapterError("native draft adapter requires a supported integer FPS")
        fps = timeline.canvas.fps_num
        transitions = {item.left_segment_id: item for item in timeline.transitions}
        tracks: list[JianyingVideoTrack | JianyingAudioTrack | JianyingTextTrack] = []
        for track in timeline.video_tracks:
            segments = []
            for segment in track.segments:
                transform = segment.transform
                if abs(transform.scale_x - transform.scale_y) > 1e-9:
                    raise JianyingAdapterError("native adapter does not support nonuniform scale")
                edge = transitions.get(segment.segment_id)
                if edge is not None and track is not timeline.video_tracks[0]:
                    raise JianyingAdapterError("native overlay transitions are not supported")
                segments.append(
                    JianyingVideoSegment(
                        source=str(sources[segment.source_id].local_path),
                        start_us=frame_to_us(
                            segment.timeline_start_frame,
                            timeline.canvas.fps_num,
                            timeline.canvas.fps_den,
                        ),
                        duration_us=frame_to_us(
                            segment.timeline_duration_frames,
                            timeline.canvas.fps_num,
                            timeline.canvas.fps_den,
                        ),
                        source_start_us=segment.visible_source_start_us,
                        source_duration_us=segment.visible_source_duration_us,
                        speed=segment.speed,
                        x=transform.x,
                        y=transform.y,
                        scale=transform.scale_x,
                        rotation=transform.rotation,
                        opacity=transform.opacity,
                        transition_out=(
                            JianyingTransition(
                                duration_us=frame_to_us(
                                    edge.duration_frames,
                                    timeline.canvas.fps_num,
                                    timeline.canvas.fps_den,
                                )
                            )
                            if edge
                            else None
                        ),
                    )
                )
            if segments:
                tracks.append(JianyingVideoTrack(name=track.name, segments=segments))
        for text_track in timeline.text_tracks:
            tracks.append(
                JianyingTextTrack(
                    name=text_track.name,
                    segments=[
                        JianyingTextSegment(
                            text=item.text,
                            start_us=frame_to_us(item.start_frame, fps, 1),
                            duration_us=frame_to_us(item.duration_frames, fps, 1),
                            size=min(100, max(1, item.style.size / 7)),
                            x=item.style.x * 2 - 1,
                            y=1 - item.style.y * 2,
                            color=item.style.color,
                            border_color=item.style.border_color,
                            border_width=min(1, item.style.border_width / 20),
                        )
                        for item in text_track.segments
                    ],
                )
            )
        for audio_track in timeline.audio_tracks:
            tracks.append(
                JianyingAudioTrack(
                    name=audio_track.name,
                    segments=[
                        JianyingAudioSegment(
                            source=str(sources[item.source_id].local_path),
                            start_us=frame_to_us(item.timeline_start_frame, fps, 1),
                            duration_us=frame_to_us(item.timeline_duration_frames, fps, 1),
                            source_start_us=item.source_start_us,
                            source_duration_us=item.source_duration_us,
                            volume=item.volume,
                        )
                        for item in audio_track.segments
                    ],
                )
            )
        plan = JianyingDraftPlan(
            name=name,
            canvas=JianyingCanvas(
                width=timeline.canvas.width,
                height=timeline.canvas.height,
                fps=cast(Literal[24, 25, 30, 50, 60], fps),
            ),
            tracks=tracks,
        )
        verify_jianying_plan(plan, timeline)
        return plan

    def build_editable_draft(
        self,
        build: RenderBuild,
        sources: MaterializedSources,
        output_root: Path,
        *,
        name: str,
    ) -> JianyingDraftResult:
        build = verify_render_build(build.root)
        plan = self.compile_plan(build, sources, name=name)
        self._run("doctor")
        output_root = output_root.resolve()
        output_root.mkdir(parents=True, mode=0o700, exist_ok=False)
        plan_path = output_root / "jianying-plan.json"
        plan_path.write_bytes(canonical_json(plan.model_dump(mode="json", by_alias=True)))
        native_build = output_root / "native-build"
        result = self._run("build", "--plan", str(plan_path), "--out", str(native_build))
        if result.get("status") != "built" or result.get("live_written") is not False:
            raise JianyingAdapterError("native builder returned an invalid build result")
        report = output_root / "verify-report.json"
        verified = self._run("verify-build", "--build", str(native_build), "--report", str(report))
        if verified.get("status") != "verified" or not report.is_file():
            raise JianyingAdapterError("native draft build verification failed")
        native_hash = content_hash(_files_manifest(native_build))
        manifest = output_root / "adapter-manifest.json"
        manifest.write_bytes(
            canonical_json(
                {
                    "schema": self.VERSION,
                    "compiled_timeline_hash": build.timeline.compiled_hash,
                    "render_build_hash": build.manifest.build_instance_hash,
                    "plan_sha256": sha256_file(plan_path),
                    "native_build_hash": native_hash,
                    "native_ui_acceptance": "pending",
                    "published": False,
                }
            )
        )
        return JianyingDraftResult(
            root=output_root,
            draft=native_build / "draft",
            plan=plan_path,
            manifest=manifest,
            compiled_timeline_hash=build.timeline.compiled_hash,
            render_build_hash=build.manifest.build_instance_hash,
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


def verify_jianying_plan(plan: JianyingDraftPlan, timeline: CompiledTimelineV2) -> None:
    video_tracks = [item for item in plan.tracks if isinstance(item, JianyingVideoTrack)]
    if len(video_tracks) != len(timeline.video_tracks):
        raise JianyingAdapterError("native video track count differs from compiled timeline")
    primary = video_tracks[0]
    cursor = 0
    for segment in primary.segments:
        if segment.start_us != cursor:
            raise JianyingAdapterError("native primary video track is not continuous")
        cursor += segment.duration_us
    if abs(cursor - timeline.duration_us) > 1:
        raise JianyingAdapterError("native plan duration differs from compiled timeline")


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
