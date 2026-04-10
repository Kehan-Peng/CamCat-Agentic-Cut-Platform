"""
测试 EditingStateReadNode 和 PlanDiffNode
"""
import pytest
from backend.app.agents.editing.editing_state_read import editing_state_read_node
from backend.app.agents.editing.plan_diff import plan_diff_node
from backend.app.agents.state import AgentState
from backend.app.domain.editing_state import GlobalEditingState


def test_editing_state_read_node_loads_existing_state():
    """测试 EditingStateReadNode 加载现有状态"""
    # 模拟已有的编辑状态
    existing_state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1", "seg_2"],
        state_version=3
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        editing_session_id="edit_001",
        query_text="测试"
    )

    # 在实际实现中，这里会从数据库加载
    # 现在我们模拟传入
    result = editing_state_read_node(state, existing_editing_state=existing_state)

    assert "global_editing_state" in result
    assert result["global_editing_state"].editing_session_id == "edit_001"
    assert result["global_editing_state"].state_version == 3


def test_editing_state_read_node_creates_new_state():
    """测试 EditingStateReadNode 创建新状态"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        video_id="video_001",
        query_text="剪成 30 秒短视频"
    )

    result = editing_state_read_node(state)

    assert "global_editing_state" in result
    assert result["global_editing_state"].user_id == "user_001"
    assert result["global_editing_state"].state_version == 1


def test_plan_diff_node_generates_minimal_patch():
    """测试 PlanDiffNode 生成最小补丁"""
    existing_state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1", "seg_2", "seg_3"],
        subtitle_draft="原始字幕",
        state_version=5
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        editing_session_id="edit_001",
        query_text="第二段删掉，字幕短一点",
        global_editing_state=existing_state,
        edit_task={
            "task_type": "general_editing",
            "instruction": "第二段删掉，字幕短一点"
        }
    )

    result = plan_diff_node(state)

    assert "editing_patch" in result
    patch = result["editing_patch"]
    assert patch.base_state_version == 5
    assert len(patch.operations) > 0
    assert patch.patch_type == "incremental"


def test_plan_diff_node_full_regeneration():
    """测试 PlanDiffNode 全量重新生成"""
    existing_state = GlobalEditingState(
        editing_session_id="edit_001",
        user_id="user_001",
        video_id="video_001",
        selected_segments=["seg_1"],
        state_version=2
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user_001",
        editing_session_id="edit_001",
        query_text="全部重来，换一个风格",
        global_editing_state=existing_state,
        edit_task={
            "task_type": "general_editing",
            "instruction": "全部重来，换一个风格"
        }
    )

    result = plan_diff_node(state)

    assert "editing_patch" in result
    patch = result["editing_patch"]
    assert patch.patch_type == "full_regeneration"
    assert patch.requires_user_confirmation is True
