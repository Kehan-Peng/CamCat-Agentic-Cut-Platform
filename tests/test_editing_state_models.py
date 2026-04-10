"""
测试 Editing State 数据模型
"""
import pytest
from backend.app.domain.editing_state import (
    GlobalEditingState,
    EditingStatePatch,
    PatchOperation,
    WorkflowArtifactStatus,
)


def test_global_editing_state_creation():
    """测试 GlobalEditingState 创建"""
    state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1", "seg_2"],
        state_version=1
    )

    assert state.editing_session_id == "edit_001"
    assert state.user_id == "user_001"
    assert state.video_id == "video_001"
    assert state.selected_segments == ["seg_1", "seg_2"]
    assert state.state_version == 1
    assert state.subtitle_draft is None
    assert state.editing_plan is None
    assert state.clip_segments == []


def test_global_editing_state_with_artifacts():
    """测试 GlobalEditingState 包含产物"""
    state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1"],
        subtitle_draft="测试字幕",
        editing_plan="测试计划",
        clip_segments=["clip_1"],
        title_candidates=["标题1", "标题2"],
        state_version=2
    )

    assert state.subtitle_draft == "测试字幕"
    assert state.editing_plan == "测试计划"
    assert state.clip_segments == ["clip_1"]
    assert state.title_candidates == ["标题1", "标题2"]


def test_workflow_artifact_status():
    """测试 WorkflowArtifactStatus"""
    status = WorkflowArtifactStatus(
        subtitle_draft="ready",
        editing_plan="ready",
        clip_segments="stale",
        title_candidates="ready",
        edited_video="not_started"
    )

    assert status.subtitle_draft == "ready"
    assert status.editing_plan == "ready"
    assert status.clip_segments == "stale"
    assert status.title_candidates == "ready"
    assert status.edited_video == "not_started"


def test_patch_operation_add_segment():
    """测试 PatchOperation - 添加片段"""
    op = PatchOperation(
        op="add_segment",
        target="selected_segments",
        value="seg_3"
    )

    assert op.op == "add_segment"
    assert op.target == "selected_segments"
    assert op.value == "seg_3"


def test_patch_operation_remove_segment():
    """测试 PatchOperation - 删除片段"""
    op = PatchOperation(
        op="remove_segment",
        target="clip_segments",
        clip_segment_id="clip_2"
    )

    assert op.op == "remove_segment"
    assert op.target == "clip_segments"
    assert op.clip_segment_id == "clip_2"


def test_patch_operation_update_subtitle_style():
    """测试 PatchOperation - 更新字幕样式"""
    op = PatchOperation(
        op="update_subtitle_style",
        target="subtitle_draft",
        value={"max_chars_per_line": 12, "style": "shorter"}
    )

    assert op.op == "update_subtitle_style"
    assert op.target == "subtitle_draft"
    assert op.value == {"max_chars_per_line": 12, "style": "shorter"}


def test_editing_state_patch_creation():
    """测试 EditingStatePatch 创建"""
    patch = EditingStatePatch(
        patch_id="patch_001",
        editing_session_id="edit_001",
        base_state_version=1,
        operations=[
            PatchOperation(
                op="add_segment",
                target="selected_segments",
                value="seg_3"
            )
        ],
        affected_artifacts=["editing_plan", "clip_segments"],
        needs_refresh={
            "editing_plan": True,
            "clip_segments": True,
            "subtitle_draft": False
        }
    )

    assert patch.patch_id == "patch_001"
    assert patch.editing_session_id == "edit_001"
    assert patch.base_state_version == 1
    assert len(patch.operations) == 1
    assert patch.operations[0].op == "add_segment"
    assert patch.affected_artifacts == ["editing_plan", "clip_segments"]
    assert patch.needs_refresh["editing_plan"] is True
    assert patch.needs_refresh["subtitle_draft"] is False


def test_editing_state_patch_with_multiple_operations():
    """测试 EditingStatePatch 包含多个操作"""
    patch = EditingStatePatch(
        patch_id="patch_002",
        editing_session_id="edit_001",
        base_state_version=2,
        operations=[
            PatchOperation(
                op="remove_segment",
                target="clip_segments",
                clip_segment_id="clip_2"
            ),
            PatchOperation(
                op="update_subtitle_style",
                target="subtitle_draft",
                value={"style": "shorter"}
            )
        ],
        affected_artifacts=["clip_segments", "subtitle_draft", "edited_video"],
        needs_refresh={
            "clip_segments": True,
            "subtitle_draft": True,
            "edited_video": True
        },
        requires_retrieval=False,
        requires_render=True
    )

    assert len(patch.operations) == 2
    assert patch.requires_retrieval is False
    assert patch.requires_render is True


def test_editing_state_patch_full_regeneration():
    """测试 EditingStatePatch 全量重新生成"""
    patch = EditingStatePatch(
        patch_id="patch_003",
        editing_session_id="edit_001",
        base_state_version=3,
        operations=[],
        affected_artifacts=["editing_plan", "clip_segments", "subtitle_draft"],
        needs_refresh={
            "editing_plan": True,
            "clip_segments": True,
            "subtitle_draft": True,
            "title_candidates": True,
            "edited_video": True
        },
        patch_type="full_regeneration",
        reason="用户明确要求完全重写",
        requires_user_confirmation=True
    )

    assert patch.patch_type == "full_regeneration"
    assert patch.reason == "用户明确要求完全重写"
    assert patch.requires_user_confirmation is True
