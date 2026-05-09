from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment, SearchQuery
from backend.app.retrieval.hybrid import HybridRetriever


def build_retrieval_node(segments: list[MediaSegment]):
    def retrieval_node(state: AgentState) -> AgentState:
        query = SearchQuery(
            query_text=_query_text_for_retrieval(state),
            user_id=state.user_id,
            session_id=state.session_id,
            scenario=state.scenario,
            top_k=state.top_k,
            filters=state.filters,
        )
        retrieved = HybridRetriever(segments).search(query)
        return state.model_copy(update={"retrieved_segments": retrieved}, deep=True)

    return retrieval_node


def _query_text_for_retrieval(state: AgentState) -> str:
    if state.rewritten_query:
        return str(state.rewritten_query.get("normalized_query") or state.query_text)
    return state.query_text
