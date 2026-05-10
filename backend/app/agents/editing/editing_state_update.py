"""
EditingStateUpdateNode

原子性地提交补丁并更新编辑状态，强制版本检查。
"""
from backend.app.agents.state import AgentState
from backend.app.domain.editing_state import GlobalEditingState, EditingStatePatch
from copy import deepcopy


def editing_state_update_node(state: AgentState) -> AgentState:
    """
    更新编辑状态

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState
    """
    global_editing_state = state.get("global_editing_state")
    editing_patch = state.get("editing_patch")

    if not global_editing_state or not editing_patch:
        raise ValueError("global_editing_state and editing_patch are required")

    # 版本检查
    if editing_patch.base_state_version != global_editing_state.state_version:
        return {
            **state,
            "update_success": False,
            "conflict_detected": True,
            "conflict_reason": f"版本冲突: 补丁基于版本 {editing_patch.base_state_version}, 但当前状态版本是 {global_editing_state.state_version}"
        }

    # 应用补丁
    updated_state = _apply_patch(global_editing_state, editing_patch)

    # 递增版本号
    updated_state.state_version += 1

    # 更新产物状态
    for artifact, needs_refresh in editing_patch.needs_refresh.items():
        if needs_refresh:
            if hasattr(updated_state.artifact_status, artifact):
                setattr(updated_state.artifact_status, artifact, "stale")

    return {
        **state,
        "global_editing_state": updated_state,
        "update_success": True,
        "conflict_detected": False
    }


def _apply_patch(
    global_editing_state: GlobalEditingState,
    editing_patch: EditingStatePatch
) -> GlobalEditingState:
    """
    应用补丁到编辑状态

    Args:
        global_editing_state: 全局编辑状态
        editing_patch: 编辑状态补丁

    Returns:
        更新后的 GlobalEditingState
    """
    # 深拷贝状态以避免修改原始对象
    updated_state = deepcopy(global_editing_state)

    # 应用每个操作
    for operation in editing_patch.operations:
        op = operation.op
        target = operation.target

        if op == "add_segment":
            if target == "selected_segments":
                if operation.value not in updated_state.selected_segments:
                    updated_state.selected_segments.append(operation.value)
            elif target == "clip_segments":
                if operation.value not in updated_state.clip_segments:
                    updated_state.clip_segments.append(operation.value)

        elif op == "remove_segment":
            if target == "clip_segments" and operation.clip_segment_id:
                if operation.clip_segment_id in updated_state.clip_segments:
                    updated_state.clip_segments.remove(operation.clip_segment_id)
            elif target == "selected_segments" and operation.segment_id:
                if operation.segment_id in updated_state.selected_segments:
                    updated_state.selected_segments.remove(operation.segment_id)

        elif op == "update_subtitle_style":
            if target == "subtitle_draft":
                # 在实际实现中，这里会更新字幕样式
                # 现在只是标记需要刷新
                pass

        elif op == "update_title_style":
            if target == "title_candidates":
                # 标记需要刷新
                pass

    return updated_state
