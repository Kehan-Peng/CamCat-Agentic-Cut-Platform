from backend.app.agents.state import AgentState
from backend.app.retrieval.query_rewrite import rewrite_query


def query_rewrite_node(state: AgentState) -> AgentState:
    rewritten = rewrite_query(state.get('query_text', ''))
    return {
        **state,
        "rewritten_query": rewritten.model_dump(),
        "expanded_queries": rewritten.expanded_queries,
    }
