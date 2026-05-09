from backend.app.agents.checkpoint import build_in_memory_checkpointer
from backend.app.agents.graph import build_agent_graph, invoke_agent_graph
from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment, SegmentEvidence


def test_graph_invocation_uses_state_thread_id_for_checkpoint_config():
    checkpointer = build_in_memory_checkpointer()
    graph = build_agent_graph([_segment("seg-a")], checkpointer=checkpointer)
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-checkpoint-1",
        user_id="user-1",
        query_text="热血 卡点",
    )

    result = invoke_agent_graph(graph, state)
    snapshot = graph.get_state({"configurable": {"thread_id": "thread-checkpoint-1"}})

    assert result.thread_id == "thread-checkpoint-1"
    assert snapshot.values["thread_id"] == "thread-checkpoint-1"
    assert snapshot.values["final_answer"] == result.final_answer


def test_graph_invocation_allows_explicit_thread_config_override():
    checkpointer = build_in_memory_checkpointer()
    graph = build_agent_graph([_segment("seg-a")], checkpointer=checkpointer)
    state = AgentState(
        graph_run_id="run-1",
        thread_id="state-thread",
        user_id="user-1",
        query_text="热血 卡点",
    )

    invoke_agent_graph(
        graph,
        state,
        config={"configurable": {"thread_id": "explicit-thread"}},
    )
    snapshot = graph.get_state({"configurable": {"thread_id": "explicit-thread"}})

    assert snapshot.values["thread_id"] == "state-thread"


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
