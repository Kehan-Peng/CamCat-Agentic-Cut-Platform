from dataclasses import replace
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.agents.planner import SearchPlan, SearchPlanner
from backend.app.agents.reflection import ReflectionResult, validate_grounding
from backend.app.agents.tools import ToolRegistry
from backend.app.domain.models import CreativeSuggestion, MediaSegment, SearchQuery
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.query_rewrite import QueryRewrite, rewrite_query
from backend.app.retrieval.rerank import rerank_results
from backend.app.suggestions.creative import build_creative_suggestion, build_overall_suggestion


class ToolTraceEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool_name: str
    input: Any = None
    status: str
    output: Any = None


class AgentSearchResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    plan: SearchPlan
    trace: list[ToolTraceEntry] = Field(default_factory=list)
    results: list[Any] = Field(default_factory=list)
    creative_suggestion: CreativeSuggestion | None = None
    final_answer: str
    reflection: ReflectionResult


class AgentSearchRuntime:
    def __init__(
        self,
        segments: list[MediaSegment],
        *,
        planner: SearchPlanner | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self._segments = segments
        self._planner = planner or SearchPlanner()
        self._registry = registry or _build_default_registry(segments)

    def run(self, query: SearchQuery) -> AgentSearchResponse:
        plan = self._planner.plan(query)
        trace: list[ToolTraceEntry] = []
        rewrite: QueryRewrite | None = None
        results: list[Any] = []
        creative_suggestion: CreativeSuggestion | None = None
        final_answer = ""
        reflection: ReflectionResult | None = None

        for step in plan.steps:
            if step.tool_name == "query_rewrite":
                rewrite = self._call_tool(trace, "query_rewrite", {"query_text": query.query_text}, query.query_text)
            elif step.tool_name == "search":
                rewritten_query = query.model_copy(
                    update={"query_text": rewrite.normalized_query if rewrite else query.query_text}
                )
                results = self._call_tool(trace, "search", rewritten_query.model_dump(), rewritten_query)
            elif step.tool_name == "rerank":
                results = self._call_tool(
                    trace,
                    "rerank",
                    {"result_count": len(results), "query_text": query.query_text},
                    results,
                    query.query_text,
                )
            elif step.tool_name == "creative_suggestion":
                creative_output = self._call_tool(
                    trace,
                    "creative_suggestion",
                    {"result_count": len(results)},
                    results,
                )
                results = creative_output["results"]
                creative_suggestion = creative_output["overall"]
                final_answer = _build_final_answer(results)
            elif step.tool_name == "reflection":
                reflection = self._call_tool(
                    trace,
                    "reflection",
                    {"result_count": len(results), "has_final_answer": bool(final_answer)},
                    final_answer,
                    results,
                )

        if reflection is None:
            reflection = validate_grounding(final_answer, results)

        return AgentSearchResponse(
            plan=plan,
            trace=trace,
            results=results,
            creative_suggestion=creative_suggestion,
            final_answer=final_answer,
            reflection=reflection,
        )

    def _call_tool(
        self,
        trace: list[ToolTraceEntry],
        tool_name: str,
        trace_input: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        try:
            output = self._registry.call(tool_name, *args, **kwargs)
        except Exception as exc:
            trace.append(
                ToolTraceEntry(
                    tool_name=tool_name,
                    input=trace_input,
                    status="error",
                    output={"error": str(exc)},
                )
            )
            raise

        trace.append(
            ToolTraceEntry(
                tool_name=tool_name,
                input=trace_input,
                status="ok",
                output=_trace_output(output),
            )
        )
        return output


def _build_default_registry(segments: list[MediaSegment]) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("query_rewrite", rewrite_query)
    registry.register("search", lambda query: HybridRetriever(segments).search(query))
    registry.register("rerank", lambda results, query_text: rerank_results(results, query_text=query_text))
    registry.register("creative_suggestion", _add_creative_suggestions)
    registry.register("reflection", validate_grounding)
    return registry


def _add_creative_suggestions(results: list[Any]) -> dict[str, Any]:
    return {
        "results": [_replace_creative_suggestion(result) for result in results],
        "overall": build_overall_suggestion(results),
    }


def _replace_creative_suggestion(result: Any) -> Any:
    try:
        return replace(result, creative_suggestion=build_creative_suggestion(result))
    except TypeError:
        return result


def _build_final_answer(results: list[Any]) -> str:
    if not results:
        return "No grounded results found."

    grounded_results = [
        (
            f"{result.segment_id} from video {result.video_id} covers "
            f"{result.start_time:.2f}-{result.end_time:.2f}s because {result.reason}"
            f" Evidence: {_first_evidence_text(result)}"
        )
        for result in results
    ]
    return f"Found {len(results)} segment(s): " + "; ".join(grounded_results)


def _first_evidence_text(result: Any) -> str:
    for evidence in getattr(result, "evidence", []) or []:
        text = getattr(evidence, "text", "")
        if text:
            return text
    return "No evidence text available."


def _trace_output(output: Any) -> Any:
    if isinstance(output, list):
        return {"count": len(output)}
    if isinstance(output, dict) and "results" in output:
        return {"result_count": len(output["results"]), "has_overall": output.get("overall") is not None}
    return output
