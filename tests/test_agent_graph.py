from backend.app.agents.graph import build_agent_graph, invoke_agent_graph
from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment, SegmentEvidence


def test_agent_graph_executes_deterministic_search_workflow():
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        top_k=1,
    )

    result = invoke_agent_graph(build_agent_graph([_segment("seg-a")]), state)

    assert result.rewritten_query["normalized_query"] == "热血 卡点"
    assert result.retrieved_segments
    assert result.reranked_segments
    assert result.creative_suggestions
    assert result.reflection_result == {"passed": True, "issues": []}
    assert result.final_answer
    assert "seg-a" in result.final_answer


def test_agent_graph_keeps_state_serializable_after_execution():
    result = invoke_agent_graph(
        build_agent_graph([_segment("seg-a")]),
        AgentState(
            graph_run_id="run-1",
            thread_id="thread-1",
            user_id="user-1",
            query_text="热血 卡点",
        ),
    )

    dumped = result.model_dump()

    assert dumped["graph_run_id"] == "run-1"
    assert dumped["thread_id"] == "thread-1"
    assert dumped["rewritten_query"]["expanded_queries"]
    assert dumped["reflection_result"]["passed"] is True


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
