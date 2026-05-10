"""
ConditionalRetryOrFinalize

决定是否完成、重试、请求澄清或返回尽力而为的结果。
强制执行重试预算。
"""
from backend.app.agents.state import AgentState


def conditional_retry_or_finalize_node(state: AgentState) -> AgentState:
    """
    决定是否重试或完成

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState
    """
    quality_check = state.get("quality_check", {})
    retry_budget = state.get("retry_budget", {})

    # 初始化重试预算（如果不存在）
    if not retry_budget:
        retry_budget = {
            "max_retrieval_attempts": 3,
            "retrieval_attempt_count": 0,
            "latency_budget_ms": 5000,
            "llm_call_budget": 5
        }

    # 获取当前重试次数
    attempt_count = retry_budget.get("retrieval_attempt_count", 0)
    max_attempts = retry_budget.get("max_retrieval_attempts", 3)
    latency_budget_ms = retry_budget.get("latency_budget_ms", 5000)

    # 检查质量是否通过
    passed = quality_check.get("passed", False)
    retry_action = quality_check.get("retry_action", "finalize")

    # 决定是否重试
    should_retry = False
    finalize_reason = None

    if passed:
        # 质量通过，完成
        finalize_reason = "quality_passed"
    elif attempt_count >= max_attempts:
        # 达到最大重试次数，完成
        finalize_reason = "max_attempts_reached"
    elif latency_budget_ms <= 0:
        # 超出延迟预算，完成
        finalize_reason = "latency_budget_exceeded"
    else:
        # 可以重试
        should_retry = True

    # 更新重试预算
    if should_retry:
        retry_budget["retrieval_attempt_count"] = attempt_count + 1
        retry_history = state.get("retry_history", [])
        retry_history.append({
            "attempt": attempt_count + 1,
            "reason": quality_check.get("retry_reason"),
            "action": retry_action
        })
    else:
        retry_history = state.get("retry_history", [])

    return {
        **state,
        "retry_budget": retry_budget,
        "retry_history": retry_history,
        "should_retry": should_retry,
        "finalize_reason": finalize_reason
    }
