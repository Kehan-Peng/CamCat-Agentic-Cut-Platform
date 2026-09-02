from copy import deepcopy

import pytest
from camcat.domain.state_patch import (
    PatchConflict,
    VersionedState,
    apply_versioned_patch,
    build_rollback_patch,
)


def initial_state() -> VersionedState:
    return VersionedState(
        session_id="session-1",
        version=3,
        document={
            "goal": "剪成 30 秒宣传片",
            "clips": [
                {
                    "clip_id": "clip-1",
                    "source_start": 0.0,
                    "source_end": 5.0,
                    "output_start": 0.0,
                    "output_end": 5.0,
                }
            ],
            "subtitles": [],
        },
    )


def test_patch_increments_version_and_does_not_mutate_prior_state() -> None:
    before = initial_state()
    snapshot = deepcopy(before.document)

    after, audit = apply_versioned_patch(
        before,
        base_version=3,
        operations=[{"op": "replace", "path": "/goal", "value": "剪成 15 秒预告片"}],
        actor="user-1",
        reason="shorter cut",
    )

    assert before.document == snapshot
    assert after.version == 4
    assert after.document["goal"] == "剪成 15 秒预告片"
    assert audit.base_version == 3
    assert audit.result_version == 4
    assert audit.operations[0].path == "/goal"


def test_audio_plan_is_an_explicit_patchable_domain_root() -> None:
    before = initial_state()
    before.document["audio_plan"] = {"bgm": [], "ambient": [], "sound_effects": []}

    after, _ = apply_versioned_patch(
        before,
        base_version=3,
        operations=[
            {
                "op": "replace",
                "path": "/audio_plan",
                "value": {
                    "bgm": [{"storage_key": "library/audio/bgm.mp3"}],
                    "ambient": [],
                    "sound_effects": [],
                },
            }
        ],
        actor="agent",
        reason="licensed sound design",
    )

    assert after.document["audio_plan"]["bgm"][0]["storage_key"].endswith("bgm.mp3")


def test_stale_base_version_raises_structured_conflict() -> None:
    with pytest.raises(PatchConflict) as caught:
        apply_versioned_patch(
            initial_state(),
            base_version=2,
            operations=[{"op": "replace", "path": "/goal", "value": "stale"}],
            actor="user-1",
            reason="stale tab",
        )

    assert caught.value.expected_version == 2
    assert caught.value.current_version == 3


@pytest.mark.parametrize("path", ["/version", "/session_id", "/clips/0/unknown"])
def test_patch_rejects_protected_or_unknown_paths(path: str) -> None:
    with pytest.raises(ValueError):
        apply_versioned_patch(
            initial_state(),
            base_version=3,
            operations=[{"op": "replace", "path": path, "value": "bad"}],
            actor="user-1",
            reason="invalid",
        )


def test_rollback_is_a_compensating_patch_not_history_deletion() -> None:
    current, audit = apply_versioned_patch(
        initial_state(),
        base_version=3,
        operations=[{"op": "replace", "path": "/goal", "value": "错误版本"}],
        actor="agent",
        reason="draft",
    )

    rollback_ops = build_rollback_patch(current.document, initial_state().document)
    restored, rollback_audit = apply_versioned_patch(
        current,
        base_version=4,
        operations=rollback_ops,
        actor="user-1",
        reason=f"rollback:{audit.patch_id}",
    )

    assert restored.version == 5
    assert restored.document == initial_state().document
    assert rollback_audit.result_version == 5
