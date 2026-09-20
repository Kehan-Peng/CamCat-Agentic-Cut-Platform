from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import jsonpatch

from camcat.domain.project import EditingProjectV2

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


def apply_versioned_patch(
    state: VersionedState,
    *,
    base_version: int,
    operations: list[dict[str, Any]] | tuple[PatchOperation, ...],
    actor: str,
    reason: str,
) -> tuple[VersionedState, PatchAudit]:
    """Apply reducer-derived internal RFC 6902 and validate the authoritative V2 project."""
    if base_version != state.version:
        raise PatchConflict(expected_version=base_version, current_version=state.version)
    if not operations:
        raise ValueError("at least one internal patch operation is required")
    raw = [
        {"op": item.op, "path": item.path, **({} if item.op == "remove" else {"value": item.value})}
        if isinstance(item, PatchOperation)
        else deepcopy(item)
        for item in operations
    ]
    try:
        document = jsonpatch.JsonPatch(raw).apply(deepcopy(state.document), in_place=False)
    except (jsonpatch.JsonPatchException, TypeError) as exc:
        raise ValueError(f"invalid internal state patch: {exc}") from exc
    validated = EditingProjectV2.model_validate(document).model_dump(mode="json", by_alias=True)
    parsed = tuple(
        PatchOperation(op=str(item["op"]), path=str(item["path"]), value=item.get("value"))
        for item in raw
    )
    result = VersionedState(state.session_id, state.version + 1, validated)
    return result, PatchAudit(
        patch_id=str(uuid4()),
        base_version=state.version,
        result_version=result.version,
        actor=actor,
        reason=reason,
        operations=parsed,
    )


def build_rollback_patch(current: JsonObject, target: JsonObject) -> list[dict[str, Any]]:
    before = EditingProjectV2.model_validate(current).model_dump(mode="json", by_alias=True)
    after = EditingProjectV2.model_validate(target).model_dump(mode="json", by_alias=True)
    operations = list(jsonpatch.JsonPatch.from_diff(before, after).patch)
    if not operations:
        raise ValueError("target version is identical to current state")
    return operations
