from backend.app.agents.state import AgentState


def test_agent_state_has_stable_serializable_defaults():
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        session_id=None,
        query_text=" 热血 卡点 ",
        scenario="content_search",
        top_k=3,
        filters={"video_id": "video-1"},
    )

    assert state.rewritten_query is None
    assert state.expanded_queries == []
    assert state.retrieved_segments == []
    assert state.reranked_segments == []
    assert state.creative_suggestions == []
    assert state.reflection_result is None
    assert state.final_answer is None
    assert state.node_trace == []
    assert state.errors == []

    dumped = state.model_dump()
    assert dumped["graph_run_id"] == "run-1"
    assert dumped["thread_id"] == "thread-1"
    assert dumped["filters"] == {"video_id": "video-1"}
    assert dumped["expanded_queries"] == []


def test_agent_state_default_collections_are_isolated():
    first = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="first",
    )
    second = AgentState(
        graph_run_id="run-2",
        thread_id="thread-2",
        user_id="user-2",
        query_text="second",
    )

    first.expanded_queries.append("热血")
    first.node_trace.append({"node_name": "query_rewrite", "status": "ok"})

    assert second.expanded_queries == []
    assert second.node_trace == []
