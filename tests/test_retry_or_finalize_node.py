"""
测试 ConditionalRetryOrFinalize
"""
import pytest
from backend.app.agents.perception.retry_or_finalize import conditional_retry_or_finalize_node
from backend.app.agents.state import AgentState


def test_retry_or_finalize_finalizes_when_quality_passed():
    """测试质量通过时完成"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        quality_check={
            "passed": True,
            "quality_score": 0.85,
            "issues": [],
            "retry_action": "finalize",
            "retry_reason": None,
            "metrics": {}
        },
        retry_budget={
            "max_retrieval_attempts": 3,
            "retrieval_attempt_count": 0,
            "latency_budget_ms": 5000,
            "llm_call_budget": 5
        }
    )

    updated = conditional_retry_or_finalize_node(state)

    assert updated.get("should_retry") is False
    assert updated.get("finalize_reason") == "quality_passed"


def test_retry_or_finalize_finalizes_when_max_attempts_reached():
    """测试达到最大重试次数时完成"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        quality_check={
            "passed": False,
            "quality_score": 0.45,
            "issues": ["结果数量不足"],
            "retry_action": "expand_query",
            "retry_reason": "结果数量不足",
            "metrics": {}
        },
        retry_budget={
            "max_retrieval_attempts": 3,
            "retrieval_attempt_count": 3,  # 已达到最大次数
            "latency_budget_ms": 5000,
            "llm_call_budget": 5
        }
    )

    updated = conditional_retry_or_finalize_node(state)

    assert updated.get("should_retry") is False
    assert updated.get("finalize_reason") == "max_attempts_reached"


def test_retry_or_finalize_finalizes_when_latency_budget_exceeded():
    """测试超出延迟预算时完成"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        quality_check={
            "passed": False,
            "quality_score": 0.45,
            "issues": ["结果数量不足"],
            "retry_action": "expand_query",
            "retry_reason": "结果数量不足",
            "metrics": {}
        },
        retry_budget={
            "max_retrieval_attempts": 3,
            "retrieval_attempt_count": 1,
            "latency_budget_ms": 0,  # 延迟预算已用完
            "llm_call_budget": 5
        }
    )

    updated = conditional_retry_or_finalize_node(state)

    assert updated.get("should_retry") is False
    assert updated.get("finalize_reason") == "latency_budget_exceeded"


def test_retry_or_finalize_enforces_retry_budget():
    """测试强制执行重试预算"""
    state = AgentState(
        graph_run_id="run-1",
        thread_id="thread-1",
        user_id="user-1",
        query_text="热血 卡点",
        quality_check={
            "passed": False,
            "quality_score": 0.45,
            "issues": ["结果数量不足"],
            "retry_action": "expand_query",
            "retry_reason": "结果数量不足",
            "metrics": {}
        },
        retry_budget={
            "max_retrieval_attempts": 3,
            "retrieval_attempt_count": 1,
            "latency_budget_ms": 5000,
            "llm_call_budget": 5
        }
    )

    updated = conditional_retry_or_finalize_node(state)

    assert updated.get("should_retry") is True
    assert updated["retry_budget"]["retrieval_attempt_count"] == 2
    assert len(updated.get("retry_history", [])) == 1
