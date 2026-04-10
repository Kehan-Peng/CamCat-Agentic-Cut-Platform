import pytest

from backend.app.agents.graph import build_agent_graph, invoke_agent_graph
from backend.app.agents.state import AgentState
from backend.app.agents.trace import trace_node
from backend.app.domain.models import MediaSegment, SegmentEvidence


def test_graph_records_serializable_node_trace_in_execution_order():
    result = invoke_agent_graph(
        build_agent_graph([_segment("seg-a")]),
        AgentState(
            graph_run_id="run-1",
            thread_id="thread-1",
            user_id="user-1",
            query_text="热血 卡点",
        ),
    )

    assert [entry["node_name"] for entry in result["node_trace"]] == [
        "query_rewrite",
        "retrieval",
        "rerank",
        "creative_suggestion",
        "final_answer",
        "reflection",
    ]
    assert [entry["status"] for entry in result["node_trace"]] == ["ok", "ok", "ok", "ok", "ok", "ok"]
    assert all(isinstance(entry["latency_ms"], float) for entry in result["node_trace"])
    assert all(entry["error"] is None for entry in result["node_trace"])


def test_trace_node_records_error_before_reraising():
    def failing_node(state: AgentState) -> AgentState:
        raise ValueError("boom")

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
    )

    with pytest.raises(ValueError, match="boom"):
        trace_node("failing_node", failing_node)(state)

    assert state["node_trace"] == [
        {
            "node_name": "failing_node",
            "status": "error",
            "latency_ms": state["node_trace"][0]["latency_ms"],
            "error": "boom",
        }
    ]


def _segment(segment_id: str) -> MediaSegment:
    return MediaSegment(
        segment_id=segment_id,
        video_id="video-1",
        user_id="user-1",
        start_time=1.0,
        end_time=3.0,
        asr_transcript="热血 卡点 高能",
        tags=["热血", "卡点"],
        motion_score=0.9,
        highlight_score=0.9,
        evidence=[
            SegmentEvidence(
                evidence_type="asr",
                text="热血 卡点 高能",
                start_time=1.0,
                end_time=3.0,
                confidence=0.9,
            )
        ],
    )
