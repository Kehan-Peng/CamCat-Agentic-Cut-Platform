from backend.app.agents.reflection import validate_grounding
from backend.app.agents.state import AgentState


def reflection_node(state: AgentState) -> AgentState:
    reflection = validate_grounding(state.final_answer, state.reranked_segments)
    return state.model_copy(update={"reflection_result": reflection.model_dump()}, deep=True)
