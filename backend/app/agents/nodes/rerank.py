from backend.app.agents.state import AgentState
from backend.app.retrieval.rerank import rerank_results


def rerank_node(state: AgentState) -> AgentState:
    reranked = rerank_results(state.retrieved_segments, query_text=state.query_text)
    return state.model_copy(update={"reranked_segments": reranked}, deep=True)
