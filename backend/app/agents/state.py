from typing import Any

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    graph_run_id: str
    thread_id: str
    user_id: str
    session_id: str | None = None
    query_text: str
    scenario: str = "content_search"
    top_k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)
    rewritten_query: dict[str, Any] | None = None
    expanded_queries: list[str] = Field(default_factory=list)
    retrieved_segments: list[Any] = Field(default_factory=list)
    reranked_segments: list[Any] = Field(default_factory=list)
    creative_suggestions: list[Any] = Field(default_factory=list)
    reflection_result: dict[str, Any] | None = None
    final_answer: str | None = None
    node_trace: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any] | str] = Field(default_factory=list)
