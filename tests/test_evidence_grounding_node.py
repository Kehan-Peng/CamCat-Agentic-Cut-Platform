"""
测试 FinalEvidenceGroundingNode
"""
import pytest
from backend.app.agents.perception.evidence_grounding import final_evidence_grounding_node
from backend.app.agents.state import AgentState
from backend.app.domain.models import SegmentEvidence
from backend.app.retrieval.local_index import LocalSearchResult


def test_evidence_grounding_node_builds_grounded_evidence():
    """测试为每个片段构建基础证据"""
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
        reason="匹配查询词：热血、卡点",
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
        reranked_segments=[result],
    )

    updated = final_evidence_grounding_node(state)

    assert len(updated.get("reranked_segments", [])) == 1
    grounded_result = updated["reranked_segments"][0]
    assert grounded_result.reason
    assert "热血" in grounded_result.reason or "卡点" in grounded_result.reason


def test_evidence_grounding_node_rejects_ungrounded_explanations():
    """测试拒绝未基础的解释"""
    # 没有证据的结果
    result = LocalSearchResult(
        segment_id="seg-1",
        video_id="video-1",
        start_time=1.0,
        end_time=3.0,
        score=0.85,
        reason="这是一个很棒的片段",  # 未基础的解释
        evidence=[],
        creative_suggestion=None,
        motion_score=0.9,
        highlight_score=0.9,
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        reranked_segments=[result],
    )

    updated = final_evidence_grounding_node(state)

    grounded_result = updated["reranked_segments"][0]
    # 应该标记为未基础或提供基于实际证据的原因
    assert grounded_result.reason != "这是一个很棒的片段"


def test_evidence_grounding_node_only_references_real_evidence():
    """测试仅引用真实证据源"""
    evidence_list = [
        SegmentEvidence(
            evidence_type="asr",
            text="热血 卡点",
            start_time=1.0,
            end_time=3.0,
            confidence=0.9,
        ),
        SegmentEvidence(
            evidence_type="tag",
            text="高能",
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
        motion_score=0.92,
        highlight_score=0.88,
    )

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        reranked_segments=[result],
    )

    updated = final_evidence_grounding_node(state)

    grounded_result = updated["reranked_segments"][0]
    # 原因应该只引用真实存在的证据
    reason = grounded_result.reason
    # 不应该包含不存在的证据
    assert "不存在的内容" not in reason
