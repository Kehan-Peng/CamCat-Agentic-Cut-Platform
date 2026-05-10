from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.app.agents.nodes import (
    build_retrieval_node,
    creative_suggestion_node,
    final_answer_node,
    query_rewrite_node,
    reflection_node,
    rerank_node,
)
from backend.app.agents.state import AgentState
from backend.app.agents.trace import trace_node
from backend.app.domain.models import MediaSegment


def build_agent_graph(segments: list[MediaSegment], *, checkpointer: Any | None = None):
    graph = StateGraph(AgentState)
    graph.add_node("query_rewrite", trace_node("query_rewrite", query_rewrite_node))
    graph.add_node("retrieval", trace_node("retrieval", build_retrieval_node(segments)))
    graph.add_node("rerank", trace_node("rerank", rerank_node))
    graph.add_node("creative_suggestion", trace_node("creative_suggestion", creative_suggestion_node))
    graph.add_node("reflection", trace_node("reflection", reflection_node))
    graph.add_node("final_answer", trace_node("final_answer", final_answer_node))

    graph.add_edge(START, "query_rewrite")
    graph.add_edge("query_rewrite", "retrieval")
    graph.add_edge("retrieval", "rerank")
    graph.add_edge("rerank", "creative_suggestion")
    graph.add_edge("creative_suggestion", "final_answer")
    graph.add_edge("final_answer", "reflection")
    graph.add_edge("reflection", END)
    return graph.compile(checkpointer=checkpointer)


def invoke_agent_graph(compiled_graph: Any, state: AgentState, config: dict[str, Any] | None = None) -> AgentState:
    result = compiled_graph.invoke(state, config=_config_with_thread_id(state, config))
    # TypedDict 不支持 isinstance 检查，直接返回结果
    return result


def _config_with_thread_id(state: AgentState, config: dict[str, Any] | None) -> dict[str, Any]:
    if config is None:
        return {"configurable": {"thread_id": state.get('thread_id')}}
    configured = dict(config)
    configurable = dict(configured.get("configurable") or {})
    configurable.setdefault("thread_id", state.get('thread_id'))
    configured["configurable"] = configurable
    return configured
