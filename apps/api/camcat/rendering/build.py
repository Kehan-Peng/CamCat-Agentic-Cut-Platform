from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from camcat.rendering.doctor import RendererCapabilityProfile
from camcat.rendering.fingerprint import (
    MediaFingerprintError,
    sha256_file,
    verify_media_fingerprint,
)
from camcat.rendering.materialization import MaterializedSources
from camcat.timeline.frames import frame_to_us
from camcat.timeline.schemas import BuildMediaRef, CompiledTimelineV2, RenderProfile
from camcat.timeline.validator import canonical_json, content_hash, verify_compiled_timeline


class BuildVerificationError(ValueError):
    pass


class RenderBuildManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_name: Literal["camcat-render-build/v2"] = Field(
        default="camcat-render-build/v2", alias="schema"
    )
    build_id: str
    session_id: str
    state_version: int
    state_hash: str
    compiled_timeline_hash: str
    source_manifest_hash: str
    render_profile_hash: str
    renderer_capability_hash: str
    build_input_digest: str
    build_created_at: datetime
    files: dict[str, dict[str, Any]]
    build_instance_hash: str


class RenderBuild(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    root: Path
    timeline: CompiledTimelineV2
    profile: RenderProfile
    capability: RendererCapabilityProfile
    manifest: RenderBuildManifest


class RenderBuildService:
    def create(
        self,
        root: Path,
        *,
        timeline: CompiledTimelineV2,
        profile: RenderProfile,
        capability: RendererCapabilityProfile,
    ) -> RenderBuild:
        verify_compiled_timeline(timeline)
        if timeline.render_profile_hash != content_hash(profile):
            raise BuildVerificationError("compiled timeline and render profile disagree")
        root = root.resolve()
        root.mkdir(parents=True, mode=0o700, exist_ok=False)
        self._write_json(
            root / "compiled-timeline.json", timeline.model_dump(mode="json", by_alias=True)
        )
        self._write_json(
            root / "source-manifest.json",
            [item.model_dump(mode="json", by_alias=True) for item in timeline.source_manifest],
        )
        self._write_json(
            root / "render-profile.json", profile.model_dump(mode="json", by_alias=True)
        )
        self._write_json(
            root / "renderer-capability.json", capability.model_dump(mode="json", by_alias=True)
        )
        if timeline.text_tracks:
            (root / "captions.ass").write_text(_captions_ass(timeline), encoding="utf-8")
        files = _files_manifest(root)
        capability_hash = content_hash(capability)
        build_input_digest = content_hash(
            {
                "state_hash": timeline.state_hash,
                "compiled_timeline_hash": timeline.compiled_hash,
                "source_manifest_hash": timeline.source_manifest_hash,
                "render_profile_hash": timeline.render_profile_hash,
                "renderer_capability_hash": capability_hash,
            }
        )
        manifest_data: dict[str, Any] = {
            "schema": "camcat-render-build/v2",
            "build_id": str(uuid4()),
            "session_id": str(timeline.session_id),
            "state_version": timeline.state_version,
            "state_hash": timeline.state_hash,
            "compiled_timeline_hash": timeline.compiled_hash,
            "source_manifest_hash": timeline.source_manifest_hash,
            "render_profile_hash": timeline.render_profile_hash,
            "renderer_capability_hash": capability_hash,
            "build_input_digest": build_input_digest,
            "build_created_at": datetime.now(UTC),
            "files": files,
            "build_instance_hash": "0" * 64,
        }
        provisional = RenderBuildManifest.model_validate(manifest_data)
        manifest = provisional.model_copy(
            update={
                "build_instance_hash": content_hash(
                    provisional.model_dump(
                        mode="json", by_alias=True, exclude={"build_instance_hash"}
                    )
                )
            }
        )
        self._write_json(
            root / "build-manifest.json", manifest.model_dump(mode="json", by_alias=True)
        )
        return verify_render_build(root)

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_bytes(canonical_json(value))
        path.chmod(0o600)


def verify_render_build(root: Path) -> RenderBuild:
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise BuildVerificationError("render build must be a regular directory")
    try:
        manifest = RenderBuildManifest.model_validate_json(
            (root / "build-manifest.json").read_bytes()
        )
        timeline = CompiledTimelineV2.model_validate_json(
            (root / "compiled-timeline.json").read_bytes()
        )
        profile = RenderProfile.model_validate_json((root / "render-profile.json").read_bytes())
        capability = RendererCapabilityProfile.model_validate_json(
            (root / "renderer-capability.json").read_bytes()
        )
    except (OSError, ValueError) as exc:
        raise BuildVerificationError(f"render build JSON is invalid: {exc}") from exc
    expected_instance = content_hash(
        manifest.model_dump(mode="json", by_alias=True, exclude={"build_instance_hash"})
    )
    if manifest.build_instance_hash != expected_instance:
        raise BuildVerificationError("build instance hash mismatch")
    if _files_manifest(root) != manifest.files:
        raise BuildVerificationError("build file manifest mismatch")
    verify_compiled_timeline(timeline)
    try:
        raw_manifest = _read_json(root / "source-manifest.json")
        source_manifest = [BuildMediaRef.model_validate(item) for item in raw_manifest]
    except (TypeError, ValueError) as exc:
        raise BuildVerificationError("source manifest is invalid") from exc
    if source_manifest != timeline.source_manifest:
        raise BuildVerificationError("source manifest differs from compiled timeline")
    if any("local_path" in item for item in raw_manifest):
        raise BuildVerificationError("persistent source manifest contains a local runtime path")
    if timeline.compiled_hash != manifest.compiled_timeline_hash:
        raise BuildVerificationError("compiled timeline hash differs from build manifest")
    if content_hash(profile) != manifest.render_profile_hash:
        raise BuildVerificationError("render profile hash differs from build manifest")
    if content_hash(capability) != manifest.renderer_capability_hash:
        raise BuildVerificationError("renderer capability hash differs from build manifest")
    expected_input = content_hash(
        {
            "state_hash": manifest.state_hash,
            "compiled_timeline_hash": manifest.compiled_timeline_hash,
            "source_manifest_hash": manifest.source_manifest_hash,
            "render_profile_hash": manifest.render_profile_hash,
            "renderer_capability_hash": manifest.renderer_capability_hash,
        }
    )
    if manifest.build_input_digest != expected_input:
        raise BuildVerificationError("build input digest mismatch")
    captions = root / "captions.ass"
    if timeline.text_tracks:
        if not captions.is_file() or captions.read_text(encoding="utf-8") != _captions_ass(
            timeline
        ):
            raise BuildVerificationError("ASS caption artifact differs from compiled timeline")
    elif captions.exists():
        raise BuildVerificationError("caption artifact exists without a text track")
    return RenderBuild(
        root=root, timeline=timeline, profile=profile, capability=capability, manifest=manifest
    )


def verify_materialized_sources(build: RenderBuild, sources: MaterializedSources) -> None:
    expected = {item.media_id: item for item in build.timeline.source_manifest}
    if set(sources) != set(expected):
        raise BuildVerificationError("materialized source identities differ from build manifest")
    try:
        for media_id, item in sources.items():
            if item.ref != expected[media_id]:
                raise BuildVerificationError(f"materialized source metadata changed: {media_id}")
            verify_media_fingerprint(item)
    except MediaFingerprintError as exc:
        raise BuildVerificationError(str(exc)) from exc


def _files_manifest(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.name == "build-manifest.json":
            continue
        if path.is_symlink():
            raise BuildVerificationError("render build cannot contain symlinks")
        if path.is_file():
            result[str(path.relative_to(root))] = {
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
    return result


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BuildVerificationError(f"invalid build JSON: {path.name}") from exc


def _captions_ass(timeline: CompiledTimelineV2) -> str:
    header = (
        "[Script Info]\nScriptType: v4.00+\n"
        f"PlayResX: {timeline.canvas.width}\nPlayResY: {timeline.canvas.height}\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,Bold,Italic,"
        "Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Default,Arial,42,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,20,20,20,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    events: list[str] = []
    for layer, track in enumerate(timeline.text_tracks):
        for item in track.segments:
            style = item.style
            start_us = frame_to_us(
                item.start_frame, timeline.canvas.fps_num, timeline.canvas.fps_den
            )
            end_us = frame_to_us(
                item.start_frame + item.duration_frames,
                timeline.canvas.fps_num,
                timeline.canvas.fps_den,
            )
            x = round(style.x * timeline.canvas.width)
            y = round(style.y * timeline.canvas.height)
            font = (style.font_family or "Arial").replace(",", " ")
            override = (
                f"{{\\fn{font}\\fs{style.size}\\pos({x},{y})"
                f"\\c&H{_ass_color(style.color)}&\\3c&H{_ass_color(style.border_color)}&"
                f"\\bord{style.border_width:g}}}"
            )
            text = (
                item.text.replace("\\", r"\\")
                .replace("{", r"\{")
                .replace("}", r"\}")
                .replace("\n", r"\N")
            )
            events.append(
                f"Dialogue: {layer},{_ass_time(start_us)},{_ass_time(end_us)},"
                f"Default,,0,0,0,,{override}{text}"
            )
    return header + "\n".join(events) + ("\n" if events else "")


def _ass_color(value: str) -> str:
    return value[5:7] + value[3:5] + value[1:3]


def _ass_time(microseconds: int) -> str:
    centiseconds = round(microseconds / 10_000)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centis:02d}"
