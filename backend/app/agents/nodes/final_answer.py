from backend.app.agents.runtime import _build_final_answer
from backend.app.agents.state import AgentState


def final_answer_node(state: AgentState) -> AgentState:
    return {
        **state,
        "final_answer": _build_final_answer(state.get('reranked_segments', []))
    }
