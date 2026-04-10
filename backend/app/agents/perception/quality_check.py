"""
SearchQualityCheckNode

执行量化检索质量评估。
不是开放式 LLM 反思步骤。
使用指标：result_count、top_score、avg_topk_score、evidence_coverage、timestamp_coverage
"""
from backend.app.agents.state import AgentState


def search_quality_check_node(state: AgentState) -> AgentState:
    """
    执行量化检索质量评估

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState，包含 quality_check 字段
    """
    reranked_segments = state.get("reranked_segments", [])
    query_text = state.get("query_text", "")
    top_k = state.get("top_k", 5)

    # 计算质量指标
    metrics = _calculate_quality_metrics(reranked_segments, query_text, top_k)

    # 检查最小质量阈值
    passed, issues, retry_action = _check_quality_thresholds(metrics, reranked_segments)

    quality_check = {
        "passed": passed,
        "quality_score": metrics.get("avg_topk_score", 0.0),
        "issues": issues,
        "retry_action": retry_action,
        "retry_reason": issues[0] if issues else None,
        "metrics": metrics
    }

    return {
        **state,
        "quality_check": quality_check
    }


def _calculate_quality_metrics(reranked_segments, query_text: str, top_k: int) -> dict:
    """
    计算质量指标

    Args:
        reranked_segments: 重排序后的片段
        query_text: 查询文本
        top_k: 期望的结果数量

    Returns:
        质量指标字典
    """
    result_count = len(reranked_segments)

    if result_count == 0:
        return {
            "result_count": 0,
            "top_score": 0.0,
            "avg_topk_score": 0.0,
            "evidence_coverage": 0.0,
            "timestamp_coverage": 1.0,
            "diversity_score": 0.0,
            "query_match_score": 0.0
        }

    # 计算分数指标
    scores = [result.score for result in reranked_segments[:top_k]]
    top_score = max(scores) if scores else 0.0
    avg_topk_score = sum(scores) / len(scores) if scores else 0.0

    # 计算证据覆盖率
    evidence_count = sum(1 for result in reranked_segments[:top_k] if result.evidence)
    evidence_coverage = evidence_count / min(result_count, top_k) if result_count > 0 else 0.0

    # 时间戳覆盖率（所有结果都有时间戳）
    timestamp_coverage = 1.0

    # 多样性分数（简化版：检查不同的 video_id）
    unique_videos = len(set(result.video_id for result in reranked_segments[:top_k]))
    diversity_score = unique_videos / min(result_count, top_k) if result_count > 0 else 0.0

    # 查询匹配分数（简化版：检查证据中是否包含查询词）
    query_terms = set(query_text.split())
    matched_count = 0
    for result in reranked_segments[:top_k]:
        if result.evidence:
            evidence_text = " ".join(e.text for e in result.evidence)
            if any(term in evidence_text for term in query_terms):
                matched_count += 1
    query_match_score = matched_count / min(result_count, top_k) if result_count > 0 else 0.0

    return {
        "result_count": result_count,
        "top_score": round(top_score, 4),
        "avg_topk_score": round(avg_topk_score, 4),
        "evidence_coverage": round(evidence_coverage, 4),
        "timestamp_coverage": round(timestamp_coverage, 4),
        "diversity_score": round(diversity_score, 4),
        "query_match_score": round(query_match_score, 4)
    }


def _check_quality_thresholds(metrics: dict, reranked_segments) -> tuple[bool, list[str], str]:
    """
    检查最小质量阈值

    Args:
        metrics: 质量指标
        reranked_segments: 重排序后的片段

    Returns:
        (passed, issues, retry_action)
    """
    issues = []

    # 最小质量阈值
    min_results = 1
    min_top_score = 0.3
    min_avg_score = 0.2
    min_evidence_coverage = 0.5

    # 检查结果数量
    if metrics["result_count"] < min_results:
        issues.append("结果数量不足")

    # 检查最高分数
    if metrics["top_score"] < min_top_score:
        issues.append(f"最高分数过低 ({metrics['top_score']:.2f} < {min_top_score})")

    # 检查平均分数
    if metrics["avg_topk_score"] < min_avg_score:
        issues.append(f"平均分数过低 ({metrics['avg_topk_score']:.2f} < {min_avg_score})")

    # 检查证据覆盖率
    if metrics["evidence_coverage"] < min_evidence_coverage:
        issues.append(f"证据覆盖率不足 ({metrics['evidence_coverage']:.2f} < {min_evidence_coverage})")

    # 决定重试动作
    if not issues:
        retry_action = "finalize"
    elif metrics["result_count"] == 0:
        retry_action = "expand_query"
    elif metrics["avg_topk_score"] < min_avg_score:
        retry_action = "adjust_filters"
    else:
        retry_action = "finalize"  # 有结果但质量不够，返回尽力而为的结果

    passed = len(issues) == 0

    return passed, issues, retry_action
