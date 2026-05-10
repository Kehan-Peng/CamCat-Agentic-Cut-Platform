from backend.app.agents.state import AgentState
from backend.app.retrieval.rerank import rerank_results


def rerank_node(state: AgentState) -> AgentState:
    reranked = rerank_results(state.get('retrieved_segments', []), query_text=state.get('query_text', ''))
    return {**state, "reranked_segments": reranked}
