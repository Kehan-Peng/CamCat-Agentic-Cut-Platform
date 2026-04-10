"""
PlanDiffNode

将用户指令转换为最小状态补丁。
"""
from backend.app.agents.state import AgentState
from backend.app.domain.editing_state import EditingStatePatch, PatchOperation
import uuid


def plan_diff_node(state: AgentState) -> AgentState:
    """
    生成编辑状态补丁

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState，包含 editing_patch
    """
    global_editing_state = state.get("global_editing_state")
    edit_task = state.get("edit_task", {})
    query_text = state.get("query_text", "")

    if not global_editing_state:
        raise ValueError("global_editing_state is required")

    # 检查是否需要全量重新生成
    if _is_full_regeneration_request(query_text):
        patch = _create_full_regeneration_patch(global_editing_state, query_text)
    else:
        patch = _create_incremental_patch(global_editing_state, edit_task, query_text)

    return {
        **state,
        "editing_patch": patch
    }


def _is_full_regeneration_request(query_text: str) -> bool:
    """
    判断是否为全量重新生成请求

    Args:
        query_text: 用户查询文本

    Returns:
        是否为全量重新生成
    """
    full_regen_keywords = ["全部重来", "重新开始", "换一个风格", "完全重写"]
    return any(keyword in query_text for keyword in full_regen_keywords)


def _create_full_regeneration_patch(
    global_editing_state,
    query_text: str
) -> EditingStatePatch:
    """
    创建全量重新生成补丁

    Args:
        global_editing_state: 全局编辑状态
        query_text: 用户查询文本

    Returns:
        EditingStatePatch
    """
    return EditingStatePatch(
        patch_id=f"patch_{uuid.uuid4().hex[:8]}",
        editing_session_id=global_editing_state.editing_session_id,
        base_state_version=global_editing_state.state_version,
        operations=[],
        affected_artifacts=["editing_plan", "clip_segments", "subtitle_draft", "title_candidates"],
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


def _create_incremental_patch(
    global_editing_state,
    edit_task: dict,
    query_text: str
) -> EditingStatePatch:
    """
    创建增量补丁

    Args:
        global_editing_state: 全局编辑状态
        edit_task: 编辑任务
        query_text: 用户查询文本

    Returns:
        EditingStatePatch
    """
    operations = []
    affected_artifacts = []
    needs_refresh = {}

    task_type = edit_task.get("task_type", "general_editing")

    # 根据任务类型生成操作
    if task_type == "segment_removal":
        operations.append(PatchOperation(
            op="remove_segment",
            target="clip_segments",
            clip_segment_id=edit_task.get("target", "segment_2")
        ))
        affected_artifacts = ["clip_segments", "edited_video"]
        needs_refresh = {
            "clip_segments": True,
            "edited_video": True,
            "subtitle_draft": False
        }

    elif task_type == "subtitle_editing":
        operations.append(PatchOperation(
            op="update_subtitle_style",
            target="subtitle_draft",
            value={"style": "shorter"}
        ))
        affected_artifacts = ["subtitle_draft", "edited_video"]
        needs_refresh = {
            "subtitle_draft": True,
            "edited_video": True,
            "clip_segments": False
        }

    elif "删" in query_text or "去掉" in query_text:
        operations.append(PatchOperation(
            op="remove_segment",
            target="clip_segments",
            clip_segment_id="clip_2"
        ))
        affected_artifacts.append("clip_segments")
        needs_refresh["clip_segments"] = True

    if "字幕" in query_text and ("短" in query_text or "长" in query_text):
        operations.append(PatchOperation(
            op="update_subtitle_style",
            target="subtitle_draft",
            value={"style": "shorter" if "短" in query_text else "longer"}
        ))
        if "subtitle_draft" not in affected_artifacts:
            affected_artifacts.append("subtitle_draft")
        needs_refresh["subtitle_draft"] = True

    # 如果有任何修改，标记 edited_video 为需要刷新
    if operations:
        if "edited_video" not in affected_artifacts:
            affected_artifacts.append("edited_video")
        needs_refresh["edited_video"] = True

    return EditingStatePatch(
        patch_id=f"patch_{uuid.uuid4().hex[:8]}",
        editing_session_id=global_editing_state.editing_session_id,
        base_state_version=global_editing_state.state_version,
        operations=operations,
        affected_artifacts=affected_artifacts,
        needs_refresh=needs_refresh,
        patch_type="incremental"
    )
