from backend.app.agents.reflection import validate_grounding
from backend.app.agents.state import AgentState


def reflection_node(state: AgentState) -> AgentState:
    reflection = validate_grounding(state.get('final_answer'), state.get('reranked_segments', []))
    return {**state, "reflection_result": reflection.model_dump()}
