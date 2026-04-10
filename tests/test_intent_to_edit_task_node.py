"""
测试 IntentToEditTaskNode
"""
import pytest
from backend.app.agents.editing.intent_to_edit_task import intent_to_edit_task_node
from backend.app.agents.state import AgentState


def test_intent_to_edit_task_node_clip_generation():
    """测试意图转编辑任务 - 剪辑生成"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="剪成 30 秒热血卡点短视频"
    )

    result = intent_to_edit_task_node(state)

    assert "edit_task" in result
    edit_task = result["edit_task"]
    assert edit_task["task_type"] == "clip_generation"
    assert "duration" in edit_task
    assert "style" in edit_task


def test_intent_to_edit_task_node_subtitle_editing():
    """测试意图转编辑任务 - 字幕编辑"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="字幕更短一点"
    )

    result = intent_to_edit_task_node(state)

    assert "edit_task" in result
    edit_task = result["edit_task"]
    assert edit_task["task_type"] == "subtitle_editing"


def test_intent_to_edit_task_node_segment_removal():
    """测试意图转编辑任务 - 片段删除"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="第二段删掉"
    )

    result = intent_to_edit_task_node(state)

    assert "edit_task" in result
    edit_task = result["edit_task"]
    assert edit_task["task_type"] == "segment_removal"
