from backend.app.agents.state import AgentState
from backend.app.domain.models import MediaSegment, SearchQuery
from backend.app.retrieval.hybrid import HybridRetriever


def build_retrieval_node(segments: list[MediaSegment]):
    def retrieval_node(state: AgentState) -> AgentState:
        query = SearchQuery(
            query_text=_query_text_for_retrieval(state),
            user_id=state.get('user_id', ''),
            session_id=state.get('session_id', ''),
            scenario=state.get('scenario', 'content_search'),
            top_k=state.get('top_k', 5),
            filters=state.get('filters', {}),
        )
        retrieved = HybridRetriever(segments).search(query)
        return {**state, "retrieved_segments": retrieved}

    return retrieval_node


def _query_text_for_retrieval(state: AgentState) -> str:
    rewritten_query = state.get('rewritten_query')
    if rewritten_query:
        return str(rewritten_query.get("normalized_query") or state.get('query_text', ''))
    return state.get('query_text', '')
