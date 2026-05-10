"""
MediaReadinessNode

检查媒体是否已索引和可搜索。
如果媒体未就绪，写入 route_request 和 readiness_status。
不直接执行媒体处理。
"""
from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment


def build_media_readiness_node(segments: list[MediaSegment]):
    """
    构建 MediaReadinessNode

    Args:
        segments: 可用的媒体片段列表

    Returns:
        media_readiness_node 函数
    """
    def media_readiness_node(state: AgentState) -> AgentState:
        """
        检查媒体就绪状态

        Args:
            state: AgentState

        Returns:
            更新后的 AgentState
        """
        # 检查实际的媒体片段可用性
        segments_available = len(segments) > 0

        if segments_available:
            # 媒体已就绪
            return {
                **state,
                "readiness_status": {
                    "status": "ready",
                    "reason": "Media is indexed and searchable"
                }
            }
        else:
            # 媒体未就绪，写入 route_request
            return {
                **state,
                "readiness_status": {
                    "status": "not_ready",
                    "reason": "Media is not indexed yet"
                },
                "route_request": "media_processing_required"
            }

    return media_readiness_node
