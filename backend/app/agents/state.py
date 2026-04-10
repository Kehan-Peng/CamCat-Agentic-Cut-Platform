"""
AgentState 定义

这是 LangGraph 运行时状态的唯一来源。
domain.models 只定义 DTOs，不定义运行时 AgentState。
"""
from typing import TypedDict, Optional, List, Dict, Any


class AgentState(TypedDict, total=False):
    """
    LangGraph Coordinator Graph 的运行时状态

    这是短暂的、可 checkpoint 的状态，不是持久化编辑的真实来源。
    """

    # 基础字段
    graph_run_id: Optional[str]
    thread_id: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    query_text: Optional[str]

    # 场景和配置
    scenario: Optional[str]
    top_k: Optional[int]
    retrieval_mode: Optional[str]
    filters: Optional[Dict[str, Any]]
    search_scope: Optional[Dict[str, Any]]
    agent_config: Optional[Dict[str, Any]]

    # 路由字段
    route_decision: Optional[str]
    route_sequence: Optional[List[str]]
    current_route_step: Optional[int]
    completed_route_steps: Optional[List[str]]
    route_request: Optional[str]
    readiness_status: Optional[Dict[str, Any]]

    # 检索字段
    rewritten_query: Optional[Dict[str, Any]]
    expanded_queries: Optional[List[str]]
    retrieved_segments: Optional[List[Any]]  # List[SearchResult]
    reranked_segments: Optional[List[Any]]   # List[SearchResult]
    evidence: Optional[List[Dict[str, Any]]]
    creative_suggestions: Optional[List[Dict[str, Any]]]
    reflection_result: Optional[Dict[str, Any]]

    # 质量检查和重试
    quality_check: Optional[Dict[str, Any]]
    retry_budget: Optional[Dict[str, Any]]
    retry_history: Optional[List[Dict[str, Any]]]

    # 编辑字段
    editing_session_id: Optional[str]
    global_editing_state_ref: Optional[str]
    editing_patch: Optional[Dict[str, Any]]
    artifact_refresh_plan: Optional[Dict[str, Any]]

    # 渲染字段
    render_job: Optional[Dict[str, Any]]

    # 响应字段
    final_answer: Optional[Dict[str, Any]]
    node_trace: Optional[List[Dict[str, Any]]]
    errors: Optional[List[Dict[str, Any]]]
