from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

JsonObject = dict[str, Any]


@dataclass(frozen=True, slots=True)
class VersionedState:
    session_id: str
    version: int
    document: JsonObject


@dataclass(frozen=True, slots=True)
class PatchOperation:
    op: str
    path: str
    value: Any = None


@dataclass(frozen=True, slots=True)
class PatchAudit:
    patch_id: str
    base_version: int
    result_version: int
    actor: str
    reason: str
    operations: tuple[PatchOperation, ...]


class PatchConflict(RuntimeError):
    def __init__(
        self,
        *,
        expected_version: int,
        current_version: int,
        current_patch: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            f"state version conflict: expected {expected_version}, current {current_version}"
        )
        self.expected_version = expected_version
        self.current_version = current_version
        self.current_patch = current_patch


_ROOTS = {
    "goal",
    "clips",
    "subtitles",
    "settings",
    "title",
    "target_duration",
    "audio_plan",
}
_CLIP_FIELDS = {
    "clip_id",
    "source_video_id",
    "segment_id",
    "source_start",
    "source_end",
    "output_start",
    "output_end",
    "transition",
    "reason",
}
_SUBTITLE_FIELDS = {"subtitle_id", "text", "start", "end", "style"}


def apply_versioned_patch(
    state: VersionedState,
    *,
    base_version: int,
    operations: list[dict[str, Any]] | tuple[PatchOperation, ...],
    actor: str,
    reason: str,
) -> tuple[VersionedState, PatchAudit]:
    if base_version != state.version:
        raise PatchConflict(expected_version=base_version, current_version=state.version)
    if not operations:
        raise ValueError("at least one patch operation is required")

    parsed = tuple(_parse_operation(item) for item in operations)
    document = deepcopy(state.document)
    for operation in parsed:
        _validate_path(operation.path)
        _apply_operation(document, operation)
    _validate_document(document)

    result = VersionedState(
        session_id=state.session_id,
        version=state.version + 1,
        document=document,
    )
    audit = PatchAudit(
        patch_id=str(uuid4()),
        base_version=state.version,
        result_version=result.version,
        actor=actor,
        reason=reason,
        operations=parsed,
    )
    return result, audit


def build_rollback_patch(current: JsonObject, target: JsonObject) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for key in sorted(set(current) | set(target)):
        if key not in _ROOTS:
            continue
        path = f"/{_escape(key)}"
        if key not in target:
            operations.append({"op": "remove", "path": path})
        elif key not in current:
            operations.append({"op": "add", "path": path, "value": deepcopy(target[key])})
        elif current[key] != target[key]:
            operations.append({"op": "replace", "path": path, "value": deepcopy(target[key])})
    if not operations:
        raise ValueError("target version is identical to current state")
    return operations


def _parse_operation(item: dict[str, Any] | PatchOperation) -> PatchOperation:
    if isinstance(item, PatchOperation):
        operation = item
    else:
        operation = PatchOperation(
            op=str(item.get("op", "")), path=str(item.get("path", "")), value=item.get("value")
        )
    if operation.op not in {"add", "replace", "remove"}:
        raise ValueError(f"unsupported patch operation: {operation.op}")
    if operation.op != "remove" and not (isinstance(item, PatchOperation) or "value" in item):
        raise ValueError(f"{operation.op} requires a value")
    return operation


def _validate_path(path: str) -> None:
    parts = _pointer_parts(path)
    if not parts or parts[0] not in _ROOTS:
        raise ValueError(f"patch path is protected or unknown: {path}")
    if parts[0] == "clips" and len(parts) > 2 and (len(parts) != 3 or parts[2] not in _CLIP_FIELDS):
        raise ValueError(f"unknown clip patch path: {path}")
    if (
        parts[0] == "subtitles"
        and len(parts) > 2
        and (len(parts) != 3 or parts[2] not in _SUBTITLE_FIELDS)
    ):
        raise ValueError(f"unknown subtitle patch path: {path}")


def _apply_operation(document: JsonObject, operation: PatchOperation) -> None:
    parts = _pointer_parts(operation.path)
    parent: Any = document
    for part in parts[:-1]:
        if isinstance(parent, list):
            parent = parent[_index(part, len(parent), allow_end=False)]
        elif isinstance(parent, dict) and part in parent:
            parent = parent[part]
        else:
            raise ValueError(f"patch parent does not exist: {operation.path}")

    leaf = parts[-1]
    if isinstance(parent, list):
        if operation.op == "add" and leaf == "-":
            parent.append(deepcopy(operation.value))
            return
        index = _index(leaf, len(parent), allow_end=operation.op == "add")
        if operation.op == "add":
            parent.insert(index, deepcopy(operation.value))
        elif operation.op == "replace":
            parent[index] = deepcopy(operation.value)
        else:
            parent.pop(index)
        return

    if not isinstance(parent, dict):
        raise ValueError(f"patch target is not a container: {operation.path}")
    if operation.op == "add":
        parent[leaf] = deepcopy(operation.value)
    elif operation.op == "replace":
        if leaf not in parent:
            raise ValueError(f"replace target does not exist: {operation.path}")
        parent[leaf] = deepcopy(operation.value)
    else:
        if leaf not in parent:
            raise ValueError(f"remove target does not exist: {operation.path}")
        del parent[leaf]


def _validate_document(document: JsonObject) -> None:
    clips = document.get("clips", [])
    if not isinstance(clips, list):
        raise ValueError("clips must be a list")
    last_output_end = 0.0
    for clip in clips:
        if not isinstance(clip, dict):
            raise ValueError("each clip must be an object")
        source_start = float(clip.get("source_start", 0))
        source_end = float(clip.get("source_end", 0))
        output_start = float(clip.get("output_start", 0))
        output_end = float(clip.get("output_end", 0))
        if min(source_start, output_start) < 0 or source_end <= source_start:
            raise ValueError("clip timecodes are invalid")
        if output_end <= output_start or output_start < last_output_end:
            raise ValueError("output timeline must be ordered with positive durations")
        last_output_end = output_end
    for subtitle in document.get("subtitles", []):
        if float(subtitle.get("start", 0)) < 0 or float(subtitle.get("end", 0)) <= float(
            subtitle.get("start", 0)
        ):
            raise ValueError("subtitle timecodes are invalid")
    audio_plan = document.get("audio_plan", {})
    if not isinstance(audio_plan, dict) or any(
        not isinstance(audio_plan.get(key, []), list) for key in ("bgm", "ambient", "sound_effects")
    ):
        raise ValueError("audio plan must contain media lists")


def _pointer_parts(path: str) -> list[str]:
    if not path.startswith("/") or path == "/":
        raise ValueError(f"invalid JSON pointer: {path}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _index(value: str, length: int, *, allow_end: bool) -> int:
    try:
        index = int(value)
    except ValueError as exc:
        raise ValueError(f"invalid list index: {value}") from exc
    maximum = length if allow_end else length - 1
    if index < 0 or index > maximum:
        raise ValueError(f"list index out of range: {value}")
    return index
