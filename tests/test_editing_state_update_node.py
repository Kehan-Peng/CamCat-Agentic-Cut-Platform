"""
测试 EditingStateUpdateNode
"""
import pytest
from backend.app.agents.editing.editing_state_update import editing_state_update_node
from backend.app.agents.state import AgentState
from backend.app.domain.editing_state import GlobalEditingState, EditingStatePatch, PatchOperation


def test_editing_state_update_node_successful_update():
    """测试 EditingStateUpdateNode 成功更新"""
    existing_state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1", "seg_2"],
        state_version=5
    )

    patch = EditingStatePatch(
        patch_id="patch_001",
        editing_session_id="edit_001",
        base_state_version=5,
        operations=[
            PatchOperation(
                op="add_segment",
                target="selected_segments",
                value="seg_3"
            )
        ],
        affected_artifacts=["editing_plan"],
        needs_refresh={"editing_plan": True}
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        global_editing_state=existing_state,
        editing_patch=patch
    )

    result = editing_state_update_node(state)

    assert "global_editing_state" in result
    updated_state = result["global_editing_state"]
    assert updated_state.state_version == 6  # 版本递增
    assert "update_success" in result
    assert result["update_success"] is True


def test_editing_state_update_node_version_conflict():
    """测试 EditingStateUpdateNode 版本冲突"""
    existing_state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1"],
        state_version=7  # 当前版本是 7
    )

    patch = EditingStatePatch(
        patch_id="patch_002",
        editing_session_id="edit_001",
        base_state_version=5,  # 补丁基于版本 5
        operations=[],
        affected_artifacts=[],
        needs_refresh={}
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        global_editing_state=existing_state,
        editing_patch=patch
    )

    result = editing_state_update_node(state)

    assert "update_success" in result
    assert result["update_success"] is False
    assert "conflict_detected" in result
    assert result["conflict_detected"] is True
    assert "conflict_reason" in result


def test_editing_state_update_node_applies_operations():
    """测试 EditingStateUpdateNode 应用操作"""
    existing_state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1", "seg_2"],
        clip_segments=["clip_1", "clip_2"],
        state_version=3
    )

    patch = EditingStatePatch(
        patch_id="patch_003",
        editing_session_id="edit_001",
        base_state_version=3,
        operations=[
            PatchOperation(
                op="remove_segment",
                target="clip_segments",
                clip_segment_id="clip_2"
            )
        ],
        affected_artifacts=["clip_segments"],
        needs_refresh={"clip_segments": True}
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        global_editing_state=existing_state,
        editing_patch=patch
    )

    result = editing_state_update_node(state)

    assert result["update_success"] is True
    updated_state = result["global_editing_state"]
    assert updated_state.state_version == 4
    # 注意：实际的操作应用逻辑需要在实现中完成
