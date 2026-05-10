"""
测试 SearchQualityCheckNode
"""
import pytest
from backend.app.agents.perception.quality_check import search_quality_check_node
from backend.app.agents.state import AgentState
from backend.app.domain.models import SegmentEvidence
from backend.app.retrieval.local_index import LocalSearchResult


def test_quality_check_node_calculates_metrics():
    """测试计算质量指标"""
    evidence_list = [
        SegmentEvidence(
            evidence_type="asr",
            text="热血 卡点 高能",
            start_time=1.0,
            end_time=3.0,
            confidence=0.9,
        )
    ]

    results = [
        LocalSearchResult(
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
        ),
        LocalSearchResult(
            segment_id="seg-2",
            video_id="video-1",
            start_time=4.0,
            end_time=6.0,
            score=0.75,
            reason="",
            evidence=evidence_list,
            creative_suggestion=None,
            motion_score=0.8,
            highlight_score=0.8,
        ),
    ]

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        top_k=2,
        reranked_segments=results,
    )

    updated = search_quality_check_node(state)

    quality_check = updated.get("quality_check")
    assert quality_check is not None
    assert "metrics" in quality_check
    metrics = quality_check["metrics"]
    assert metrics["result_count"] == 2
    assert metrics["top_score"] == 0.85
    assert 0.7 < metrics["avg_topk_score"] < 0.9


def test_quality_check_node_checks_minimum_thresholds():
    """测试检查最小质量阈值"""
    # 低质量结果
    results = [
        LocalSearchResult(
            segment_id="seg-1",
            video_id="video-1",
            start_time=1.0,
            end_time=3.0,
            score=0.15,  # 低分数
            reason="",
            evidence=[],  # 无证据
            creative_suggestion=None,
            motion_score=0.5,
            highlight_score=0.5,
        ),
    ]

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        top_k=2,
        reranked_segments=results,
    )

    updated = search_quality_check_node(state)

    quality_check = updated.get("quality_check")
    assert quality_check is not None
    assert quality_check["passed"] is False
    assert len(quality_check["issues"]) > 0


def test_quality_check_node_returns_passed_and_retry_action():
    """测试返回 passed/failed 和 retry_action"""
    # 高质量结果
    evidence_list = [
        SegmentEvidence(
            evidence_type="asr",
            text="热血 卡点 高能",
            start_time=1.0,
            end_time=3.0,
            confidence=0.9,
        )
    ]

    results = [
        LocalSearchResult(
            segment_id="seg-1",
            video_id="video-1",
            start_time=1.0,
            end_time=3.0,
            score=0.92,
            reason="",
            evidence=evidence_list,
            creative_suggestion=None,
            motion_score=0.9,
            highlight_score=0.9,
        ),
        LocalSearchResult(
            segment_id="seg-2",
            video_id="video-1",
            start_time=4.0,
            end_time=6.0,
            score=0.88,
            reason="",
            evidence=evidence_list,
            creative_suggestion=None,
            motion_score=0.85,
            highlight_score=0.85,
        ),
    ]

    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        top_k=2,
        reranked_segments=results,
    )

    updated = search_quality_check_node(state)

    quality_check = updated.get("quality_check")
    assert quality_check is not None
    assert quality_check["passed"] is True
    assert quality_check["retry_action"] == "finalize"
    assert quality_check["issues"] == []
