from backend.app.agents.runtime import _add_creative_suggestions
from backend.app.agents.state import AgentState


def creative_suggestion_node(state: AgentState) -> AgentState:
    creative_output = _add_creative_suggestions(state.reranked_segments)
    return state.model_copy(
        update={
            "reranked_segments": creative_output["results"],
            "creative_suggestions": [creative_output["overall"].model_dump()],
        },
        deep=True,
    )
