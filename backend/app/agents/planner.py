from pydantic import BaseModel

from backend.app.domain.models import SearchQuery


class SearchPlanStep(BaseModel):
    name: str
    tool_name: str


class SearchPlan(BaseModel):
    steps: list[SearchPlanStep]


class SearchPlanner:
    def plan(self, query: SearchQuery) -> SearchPlan:
        if query.scenario != "content_search":
            raise ValueError(f"unsupported search scenario: {query.scenario}")

        return SearchPlan(
            steps=[
                SearchPlanStep(name="Rewrite query", tool_name="query_rewrite"),
                SearchPlanStep(name="Retrieve candidate segments", tool_name="search"),
                SearchPlanStep(name="Rerank candidates", tool_name="rerank"),
                SearchPlanStep(name="Build creative suggestion", tool_name="creative_suggestion"),
                SearchPlanStep(name="Validate grounding", tool_name="reflection"),
            ]
        )
