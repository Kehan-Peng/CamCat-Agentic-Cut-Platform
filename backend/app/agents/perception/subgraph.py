"""
Perception & Retrieval Subgraph

完整的感知与检索子图，包含 8 个节点的完整流程。
"""
from langgraph.graph import StateGraph, END
from backend.app.agents.state import AgentState
from backend.app.agents.perception.media_readiness import build_media_readiness_node
from backend.app.agents.nodes.query_rewrite import query_rewrite_node
from backend.app.agents.nodes.retrieval import build_retrieval_node
from backend.app.agents.perception.evidence_attach import candidate_evidence_attach_node
from backend.app.agents.nodes.rerank import rerank_node
from backend.app.agents.perception.evidence_grounding import final_evidence_grounding_node
from backend.app.agents.perception.quality_check import search_quality_check_node
from backend.app.agents.perception.retry_or_finalize import conditional_retry_or_finalize_node
from backend.app.domain.models import MediaSegment


def create_perception_subgraph(segments: list[MediaSegment]):
    """
    创建 Perception & Retrieval Subgraph

    流程:
    1. MediaReadinessNode - 检查媒体就绪状态
    2. QueryRewriteNode - 查询重写
    3. HybridRetrievalNode - 混合检索
    4. CandidateEvidenceAttachNode - 附加候选证据
    5. RerankNode - 重排序
    6. FinalEvidenceGroundingNode - 最终证据接地
    7. SearchQualityCheckNode - 搜索质量检查
    8. ConditionalRetryOrFinalize - 条件重试或完成

    Args:
        segments: 可用的媒体片段列表

    Returns:
        编译后的 Perception Subgraph
    """
    workflow = StateGraph(AgentState)

    # 添加所有节点
    workflow.add_node("media_readiness", build_media_readiness_node(segments))
    workflow.add_node("query_rewrite", query_rewrite_node)
    workflow.add_node("hybrid_retrieval", build_retrieval_node(segments))
    workflow.add_node("evidence_attach", candidate_evidence_attach_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("evidence_grounding", final_evidence_grounding_node)
    workflow.add_node("quality_check", search_quality_check_node)
    workflow.add_node("retry_or_finalize", conditional_retry_or_finalize_node)

    # 设置入口点
    workflow.set_entry_point("media_readiness")

    # 添加条件边：media_readiness 根据就绪状态决定下一步
    def route_after_media_readiness(state: AgentState) -> str:
        """根据媒体就绪状态路由"""
        readiness_status = state.get("readiness_status", {})
        if readiness_status.get("status") == "ready":
            return "query_rewrite"
        else:
            # 媒体未就绪，直接结束（由 Coordinator 处理 route_request）
            return END

    workflow.add_conditional_edges(
        "media_readiness",
        route_after_media_readiness,
        {
            "query_rewrite": "query_rewrite",
            END: END
        }
    )

    # 线性流程：query_rewrite -> hybrid_retrieval -> evidence_attach -> rerank -> evidence_grounding -> quality_check -> retry_or_finalize
    workflow.add_edge("query_rewrite", "hybrid_retrieval")
    workflow.add_edge("hybrid_retrieval", "evidence_attach")
    workflow.add_edge("evidence_attach", "rerank")
    workflow.add_edge("rerank", "evidence_grounding")
    workflow.add_edge("evidence_grounding", "quality_check")
    workflow.add_edge("quality_check", "retry_or_finalize")

    # 添加条件边：retry_or_finalize 根据质量检查结果决定是否重试
    def route_after_retry_check(state: AgentState) -> str:
        """根据重试决策路由"""
        should_retry = state.get("should_retry", False)
        if should_retry:
            # 重试：回到 query_rewrite
            return "query_rewrite"
        else:
            # 完成：结束子图
            return END

    workflow.add_conditional_edges(
        "retry_or_finalize",
        route_after_retry_check,
        {
            "query_rewrite": "query_rewrite",
            END: END
        }
    )

    # 编译
    return workflow.compile()
