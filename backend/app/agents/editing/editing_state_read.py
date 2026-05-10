"""
EditingStateReadNode

读取或创建编辑状态。
"""
from backend.app.agents.state import AgentState
from backend.app.domain.editing_state import GlobalEditingState
import uuid


def editing_state_read_node(state: AgentState, existing_editing_state: GlobalEditingState = None) -> AgentState:
    """
    读取或创建编辑状态

    Args:
        state: AgentState
        existing_editing_state: 可选的现有编辑状态（用于测试）

    Returns:
        更新后的 AgentState，包含 global_editing_state
    """
    editing_session_id = state.get("editing_session_id")

    # 如果提供了现有状态，直接使用
    if existing_editing_state:
        return {
            **state,
            "global_editing_state": existing_editing_state
        }

    # 如果有 editing_session_id，尝试加载现有状态
    if editing_session_id:
        # 在实际实现中，这里会从数据库加载
        # 现在返回一个模拟的状态
        loaded_state = _load_editing_state(editing_session_id, state.get("user_id"))
        if loaded_state:
            return {
                **state,
                "global_editing_state": loaded_state
            }

    # 创建新的编辑状态
    new_state = _create_new_editing_state(state)
    return {
        **state,
        "global_editing_state": new_state
    }


def _load_editing_state(editing_session_id: str, user_id: str) -> GlobalEditingState | None:
    """
    从数据库加载编辑状态（模拟实现）

    Args:
        editing_session_id: 编辑会话 ID
        user_id: 用户 ID

    Returns:
        GlobalEditingState 或 None
    """
    # 在实际实现中，这里会查询数据库
    # 现在返回 None 表示未找到
    return None


def _create_new_editing_state(state: AgentState) -> GlobalEditingState:
    """
    创建新的编辑状态

    Args:
        state: AgentState

    Returns:
        新的 GlobalEditingState
    """
    editing_session_id = state.get("editing_session_id") or f"edit_{uuid.uuid4().hex[:8]}"

    return GlobalEditingState(
        editing_session_id=editing_session_id,
        user_id=state.get("user_id", ""),
        video_id=state.get("video_id", ""),
        selected_segments=[],
        state_version=1
    )
