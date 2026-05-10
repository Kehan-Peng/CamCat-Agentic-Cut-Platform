"""
测试 CandidateEvidenceAttachNode
"""
import pytest
from backend.app.agents.perception.evidence_attach import candidate_evidence_attach_node
from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment, SegmentEvidence, CreativeSuggestion
from backend.app.retrieval.local_index import LocalSearchResult


def test_evidence_attach_node_attaches_asr_evidence():
    """测试附加 ASR 证据到候选结果"""
    evidence_list = [
        SegmentEvidence(
            evidence_type="asr",
            text="热血 卡点 高能",
            start_time=1.0,
            end_time=3.0,
            confidence=0.9,
        )
    ]

    result = LocalSearchResult(
        segment_id="seg-1",
        video_id="video-1",
        start_time=1.0,
        end_time=3.0,
        score=0.85,
        reason="",
        evidence=evidence_list,
        creative_suggestion=None,
        motion_score=0.9,
        highlight_score=0.9,
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        retrieved_segments=[result],
    )

    updated = candidate_evidence_attach_node(state)

    assert len(updated.get("retrieved_segments", [])) == 1
    attached_result = updated["retrieved_segments"][0]
    assert attached_result.evidence
    assert len(attached_result.evidence) == 1
    assert attached_result.evidence[0].evidence_type == "asr"
    assert "热血" in attached_result.evidence[0].text


def test_evidence_attach_node_attaches_multiple_evidence_types():
    """测试附加多种类型的证据"""
    evidence_list = [
        SegmentEvidence(
            evidence_type="asr",
            text="热血 卡点 高能",
            start_time=1.0,
            end_time=3.0,
            confidence=0.9,
        ),
        SegmentEvidence(
            evidence_type="tag",
            text="热血",
            start_time=1.0,
            end_time=3.0,
            confidence=1.0,
        ),
    ]

    result = LocalSearchResult(
        segment_id="seg-1",
        video_id="video-1",
        start_time=1.0,
        end_time=3.0,
        score=0.85,
        reason="",
        evidence=evidence_list,
        creative_suggestion=None,
        motion_score=0.9,
        highlight_score=0.9,
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        retrieved_segments=[result],
    )

    updated = candidate_evidence_attach_node(state)

    attached_result = updated["retrieved_segments"][0]
    assert len(attached_result.evidence) == 2
    evidence_types = {e.evidence_type for e in attached_result.evidence}
    assert "asr" in evidence_types
    assert "tag" in evidence_types


def test_evidence_attach_node_attaches_scores():
    """测试附加 motion_score 和 highlight_score"""
    result = LocalSearchResult(
        segment_id="seg-1",
        video_id="video-1",
        start_time=1.0,
        end_time=3.0,
        score=0.85,
        reason="",
        evidence=[],
        creative_suggestion=None,
        motion_score=0.92,
        highlight_score=0.88,
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        retrieved_segments=[result],
    )

    updated = candidate_evidence_attach_node(state)

    attached_result = updated["retrieved_segments"][0]
    assert attached_result.motion_score == 0.92
    assert attached_result.highlight_score == 0.88
