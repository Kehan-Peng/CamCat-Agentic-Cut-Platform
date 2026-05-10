"""
IntentToEditTaskNode

将用户指令转换为结构化的编辑任务。
"""
from backend.app.agents.state import AgentState


def intent_to_edit_task_node(state: AgentState) -> AgentState:
    """
    将用户意图转换为编辑任务

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState，包含 edit_task
    """
    query_text = state.get("query_text", "")

    # 简单的规则匹配（生产环境应使用 LLM 或更复杂的分类器）
    edit_task = _parse_edit_intent(query_text)

    return {
        **state,
        "edit_task": edit_task
    }


def _parse_edit_intent(query_text: str) -> dict:
    """
    解析编辑意图

    Args:
        query_text: 用户查询文本

    Returns:
        编辑任务字典
    """
    query_lower = query_text.lower()

    # 剪辑生成
    if "剪成" in query_text or "短视频" in query_text:
        task = {
            "task_type": "clip_generation",
            "duration": _extract_duration(query_text),
            "style": _extract_style(query_text)
        }
        return task

    # 字幕编辑
    if "字幕" in query_text:
        return {
            "task_type": "subtitle_editing",
            "action": "update_style" if "短" in query_text or "长" in query_text else "regenerate"
        }

    # 片段删除
    if "删" in query_text or "去掉" in query_text:
        return {
            "task_type": "segment_removal",
            "target": _extract_segment_reference(query_text)
        }

    # 片段替换
    if "换" in query_text or "替换" in query_text:
        return {
            "task_type": "segment_replacement",
            "target": _extract_segment_reference(query_text)
        }

    # 标题/标签更新
    if "标题" in query_text or "标签" in query_text:
        return {
            "task_type": "title_tag_update"
        }

    # 导出请求
    if "导出" in query_text or "渲染" in query_text:
        return {
            "task_type": "export_request",
            "format": _extract_format(query_text)
        }

    # 默认：通用编辑
    return {
        "task_type": "general_editing",
        "instruction": query_text
    }


def _extract_duration(query_text: str) -> int | None:
    """提取时长（秒）"""
    import re
    match = re.search(r'(\d+)\s*秒', query_text)
    if match:
        return int(match.group(1))
    return None


def _extract_style(query_text: str) -> str:
    """提取风格"""
    if "热血" in query_text or "卡点" in query_text:
        return "energetic"
    if "温馨" in query_text:
        return "warm"
    if "快节奏" in query_text:
        return "fast_paced"
    return "default"


def _extract_segment_reference(query_text: str) -> str | None:
    """提取片段引用"""
    import re
    match = re.search(r'第(\d+)段', query_text)
    if match:
        return f"segment_{match.group(1)}"
    return None


def _extract_format(query_text: str) -> str:
    """提取导出格式"""
    if "tiktok" in query_text.lower() or "抖音" in query_text:
        return "tiktok"
    if "youtube" in query_text.lower():
        return "youtube"
    return "default"
