from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from camcat.rendering.fingerprint import (
    MediaFingerprintError,
    sha256_file,
    verify_media_fingerprint,
)
from camcat.timeline.schemas import CompiledTimeline, MediaFingerprint, RenderProfile
from camcat.timeline.validator import canonical_json, content_hash, verify_compiled_timeline


class BuildVerificationError(ValueError):
    pass


class RenderBuildManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_name: Literal["camcat-render-build/v1"] = Field(
        default="camcat-render-build/v1", alias="schema"
    )
    session_id: str
    state_version: int
    state_hash: str
    compiled_timeline_hash: str
    source_manifest_hash: str
    render_profile_hash: str
    renderer_version: str
    build_created_at: datetime
    files: dict[str, dict[str, Any]]
    build_hash: str


class RenderBuild(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    root: Path
    timeline: CompiledTimeline
    profile: RenderProfile
    manifest: RenderBuildManifest


class RenderBuildService:
    def __init__(self, *, renderer_version: str) -> None:
        self.renderer_version = renderer_version

    def create(
        self,
        root: Path,
        *,
        timeline: CompiledTimeline,
        profile: RenderProfile,
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
        if timeline.subtitles:
            (root / "subtitles.srt").write_text(_subtitles_srt(timeline), encoding="utf-8")
        files = _files_manifest(root)
        manifest_data: dict[str, Any] = {
            "schema": "camcat-render-build/v1",
            "session_id": str(timeline.session_id),
            "state_version": timeline.state_version,
            "state_hash": timeline.state_hash,
            "compiled_timeline_hash": timeline.compiled_hash,
            "source_manifest_hash": timeline.source_manifest_hash,
            "render_profile_hash": timeline.render_profile_hash,
            "renderer_version": self.renderer_version,
            "build_created_at": datetime.now(UTC),
            "files": files,
            "build_hash": "0" * 64,
        }
        provisional = RenderBuildManifest.model_validate(manifest_data)
        manifest = provisional.model_copy(
            update={
                "build_hash": content_hash(
                    provisional.model_dump(mode="json", by_alias=True, exclude={"build_hash"})
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
    except (OSError, ValueError) as exc:
        raise BuildVerificationError("render build manifest is invalid") from exc
    expected_hash = content_hash(
        manifest.model_dump(mode="json", by_alias=True, exclude={"build_hash"})
    )
    if manifest.build_hash != expected_hash:
        raise BuildVerificationError("build manifest hash mismatch")
    if _files_manifest(root) != manifest.files:
        raise BuildVerificationError("build file manifest mismatch")
    try:
        timeline = CompiledTimeline.model_validate_json(
            (root / "compiled-timeline.json").read_bytes()
        )
        source_manifest_payload = _read_json(root / "source-manifest.json")
        if not isinstance(source_manifest_payload, list):
            raise BuildVerificationError("source manifest must be a list")
        source_manifest = [
            MediaFingerprint.model_validate(item) for item in source_manifest_payload
        ]
        profile = RenderProfile.model_validate_json((root / "render-profile.json").read_bytes())
        verify_compiled_timeline(timeline)
    except (OSError, ValueError) as exc:
        raise BuildVerificationError(f"compiled timeline verification failed: {exc}") from exc
    if timeline.compiled_hash != manifest.compiled_timeline_hash:
        raise BuildVerificationError("compiled timeline hash differs from build manifest")
    if (
        timeline.state_hash != manifest.state_hash
        or timeline.state_version != manifest.state_version
    ):
        raise BuildVerificationError("state provenance differs from build manifest")
    if content_hash(profile) != manifest.render_profile_hash:
        raise BuildVerificationError("render profile hash differs from build manifest")
    if source_manifest != timeline.source_manifest:
        raise BuildVerificationError("source manifest differs from compiled timeline")
    subtitles_path = root / "subtitles.srt"
    if timeline.subtitles:
        if not subtitles_path.is_file() or subtitles_path.read_text(
            encoding="utf-8"
        ) != _subtitles_srt(timeline):
            raise BuildVerificationError("subtitle artifact differs from compiled timeline")
    elif subtitles_path.exists():
        raise BuildVerificationError("subtitle artifact exists without compiled subtitles")
    try:
        for item in timeline.source_manifest:
            verify_media_fingerprint(item)
    except MediaFingerprintError as exc:
        raise BuildVerificationError(str(exc)) from exc
    return RenderBuild(root=root, timeline=timeline, profile=profile, manifest=manifest)


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


def _subtitles_srt(timeline: CompiledTimeline) -> str:
    blocks: list[str] = []
    for index, item in enumerate(timeline.subtitles, start=1):
        start_us = round(item.target_start_frame * 1_000_000 * timeline.fps_den / timeline.fps_num)
        end_us = round(item.target_end_frame * 1_000_000 * timeline.fps_den / timeline.fps_num)
        blocks.append(
            f"{index}\n{_srt_time(start_us)} --> {_srt_time(end_us)}\n"
            f"{item.text.replace(chr(13), ' ').strip()}\n"
        )
    return "\n".join(blocks)


def _srt_time(microseconds: int) -> str:
    milliseconds = round(max(0, microseconds) / 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
