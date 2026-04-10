"""
FinalEvidenceGroundingNode

为每个返回的片段构建最终基础证据。
确保原因仅引用真实证据。
拒绝或标记未基础的解释。
"""
from backend.app.agents.state import AgentState
from backend.app.retrieval.local_index import LocalSearchResult
from dataclasses import replace


def final_evidence_grounding_node(state: AgentState) -> AgentState:
    """
    为每个片段构建基础证据

    Args:
        state: AgentState

    Returns:
        更新后的 AgentState
    """
    reranked_segments = state.get("reranked_segments", [])
    query_text = state.get("query_text", "")

    grounded_segments = []
    for result in reranked_segments:
        # 构建基于真实证据的原因
        reason = _build_grounded_reason(result, query_text)

        # 创建新的结果，替换原因
        grounded_result = replace(result, reason=reason)
        grounded_segments.append(grounded_result)

    return {
        **state,
        "reranked_segments": grounded_segments
    }


def _build_grounded_reason(result: LocalSearchResult, query_text: str) -> str:
    """
    构建基于真实证据的原因

    Args:
        result: 检索结果
        query_text: 查询文本

    Returns:
        基础原因
    """
    reasons = []

    # 从证据中提取匹配的内容
    if result.evidence:
        evidence_texts = [e.text for e in result.evidence if e.text]
        if evidence_texts:
            # 检查哪些证据文本与查询相关
            query_terms = set(query_text.split())
            matched_terms = []
            for evidence_text in evidence_texts:
                for term in query_terms:
                    if term in evidence_text and term not in matched_terms:
                        matched_terms.append(term)

            if matched_terms:
                reasons.append(f"匹配查询词：{', '.join(matched_terms)}")

    # 从标签中提取匹配
    if result.matched_tags:
        reasons.append(f"标签匹配：{', '.join(result.matched_tags)}")

    # 从分数中提取信息
    if result.motion_score >= 0.8:
        reasons.append("高动作强度")
    if result.highlight_score >= 0.8:
        reasons.append("高亮度片段")

    # 如果没有找到任何基础证据，返回通用原因
    if not reasons:
        if result.evidence:
            reasons.append("包含相关内容")
        else:
            reasons.append("基于检索分数匹配")

    return "；".join(reasons)
