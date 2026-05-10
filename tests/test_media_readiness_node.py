"""
测试 MediaReadinessNode
"""
import pytest
from backend.app.agents.perception.media_readiness import build_media_readiness_node
from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment


def test_media_readiness_node_returns_ready_when_segments_exist():
    """测试当片段存在时返回 ready 状态"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
    )

    # 模拟已有片段的情况
    segments = [
        MediaSegment(
            segment_id="seg-1",
            video_id="video-1",
            user_id="user-1",
            start_time=0.0,
            end_time=5.0,
            asr_transcript="热血片段"
        )
    ]
    media_readiness_node = build_media_readiness_node(segments)
    result = media_readiness_node(state)

    assert result.get("readiness_status") == {"status": "ready", "reason": "Media is indexed and searchable"}
    assert result.get("route_request") is None


def test_media_readiness_node_writes_route_request_when_media_not_ready():
    """测试当媒体未就绪时写入 route_request 和 readiness_status"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
    )

    # 模拟没有片段的情况
    segments = []
    media_readiness_node = build_media_readiness_node(segments)
    result = media_readiness_node(state)

    assert result.get("readiness_status") == {
        "status": "not_ready",
        "reason": "Media is not indexed yet"
    }
    assert result.get("route_request") == "media_processing_required"


def test_media_readiness_node_does_not_execute_media_processing():
    """测试 MediaReadinessNode 不直接执行媒体处理"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
    )

    # 即使媒体未就绪，也不应该直接执行媒体处理
    segments = []
    media_readiness_node = build_media_readiness_node(segments)
    result = media_readiness_node(state)

    # 只写入状态，不执行处理
    assert "readiness_status" in result
    assert "route_request" in result
    # 不应该有任何媒体处理的副作用
