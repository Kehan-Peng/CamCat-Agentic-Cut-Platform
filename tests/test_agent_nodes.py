from backend.app.agents.nodes.creative import creative_suggestion_node
from backend.app.agents.nodes.final_answer import final_answer_node
from backend.app.agents.nodes.query_rewrite import query_rewrite_node
from backend.app.agents.nodes.reflection import reflection_node
from backend.app.agents.nodes.rerank import rerank_node
from backend.app.agents.nodes.retrieval import build_retrieval_node
from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment, SegmentEvidence


def test_query_rewrite_node_populates_rewrite_fields():
    state = _state(query_text="帮我找适合做热血卡点的视频素材")

    updated = query_rewrite_node(state)

    assert updated.rewritten_query["original_query"] == "帮我找适合做热血卡点的视频素材"
    assert "high_energy" in updated.expanded_queries


def test_retrieval_and_rerank_nodes_use_existing_search_results():
    state = _state(query_text="热血 卡点", top_k=2)
    retrieval_node = build_retrieval_node([_segment("seg-b", 0.7), _segment("seg-a", 0.95)])

    retrieved = retrieval_node(state)
    reranked = rerank_node(retrieved)

    assert len(retrieved.retrieved_segments) == 2
    assert [result.segment_id for result in reranked.reranked_segments] == ["seg-a", "seg-b"]
    assert reranked.reranked_segments[0].score >= reranked.reranked_segments[1].score
    assert all(result.score >= 0 for result in reranked.reranked_segments)


def test_creative_reflection_and_final_answer_nodes_populate_outputs():
    state = _state(query_text="热血 卡点", top_k=1)
    state = build_retrieval_node([_segment("seg-a", 0.95)])(state)
    state = rerank_node(state)

    with_creative = creative_suggestion_node(state)
    with_answer = final_answer_node(with_creative)
    reflected = reflection_node(with_answer)

    assert with_creative.creative_suggestions
    assert with_creative.creative_suggestions[0]["recommended_bgm_style"]
    assert with_answer.reflection_result is None
    assert reflected.final_answer
    assert "seg-a" in reflected.final_answer
    assert reflected.reflection_result == {"passed": True, "issues": []}


def _state(query_text: str, top_k: int = 3) -> AgentState:
    return AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text=query_text,
        top_k=top_k,
    )


def _segment(segment_id: str, highlight_score: float) -> MediaSegment:
    return MediaSegment(
        segment_id=segment_id,
        video_id="video-1",
        user_id="user-1",
        start_time=1.0,
        end_time=3.0,
        asr_transcript="热血 卡点 高能",
        tags=["热血", "卡点"],
        motion_score=0.9,
        highlight_score=highlight_score,
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
