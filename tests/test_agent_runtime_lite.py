import pytest

import backend.app.agents.runtime as runtime_module
from backend.app.agents.planner import SearchPlanner
from backend.app.agents.reflection import validate_grounding
from backend.app.agents.runtime import AgentSearchRuntime
from backend.app.agents.tools import ToolRegistry, UnknownToolError
from backend.app.domain.models import MediaSegment, SearchQuery, SegmentEvidence


def test_legacy_runtime_is_marked_as_compatibility_layer():
    assert runtime_module.__doc__
    assert "compatibility layer" in runtime_module.__doc__


def test_planner_returns_deterministic_content_search_steps():
    plan = SearchPlanner().plan(SearchQuery(query_text="热血卡点", user_id="user-1"))

    assert [step.tool_name for step in plan.steps] == [
        "query_rewrite",
        "search",
        "rerank",
        "creative_suggestion",
        "reflection",
    ]


def test_tool_registry_calls_registered_tool_and_rejects_unknown_tool():
    registry = ToolRegistry()
    registry.register("double", lambda value: value * 2)

    assert registry.call("double", 3) == 6

    with pytest.raises(UnknownToolError):
        registry.call("missing")


def test_runtime_records_tool_trace_deterministically():
    runtime = AgentSearchRuntime(segments=[_segment("seg-b"), _segment("seg-a")])
    query = SearchQuery(query_text="热血 卡点", user_id="user-1", top_k=2)

    response = runtime.run(query)

    assert [entry.tool_name for entry in response.trace] == [
        "query_rewrite",
        "search",
        "rerank",
        "creative_suggestion",
        "reflection",
    ]
    assert [entry.status for entry in response.trace] == ["ok", "ok", "ok", "ok", "ok"]
    assert response.results
    assert response.reflection.passed is True
    assert response.reflection.issues == []
    assert response.final_answer
    for result in response.results:
        assert result.segment_id in response.final_answer
        assert f"{result.start_time:.2f}-{result.end_time:.2f}s" in response.final_answer
        assert result.reason in response.final_answer


def test_reflection_fails_when_result_lacks_timestamp_evidence_or_reason():
    reflection = validate_grounding(
        final_answer="Found a segment.",
        results=[
            {
                "segment_id": "seg-1",
                "video_id": "video-1",
                "score": 0.8,
                "reason": "",
                "evidence": [],
            }
        ],
    )

    assert reflection.passed is False
    assert "missing_timestamp" in reflection.issues
    assert "missing_evidence" in reflection.issues
    assert "missing_reason" in reflection.issues


def test_reflection_fails_when_any_result_lacks_grounding_fields():
    reflection = validate_grounding(
        final_answer=(
            "Found segment seg-1 at 1.0-3.0s because tags matched the query with evidence 热血. "
            "Found segment seg-2 at 4.0-6.0s because tags matched the query with evidence 卡点."
        ),
        results=[
            {
                "segment_id": "seg-1",
                "video_id": "video-1",
                "start_time": 1.0,
                "end_time": 3.0,
                "score": 0.8,
                "reason": "tags matched the query",
                "evidence": [{"evidence_type": "tag", "text": "热血", "start_time": 1.0}],
            },
            {
                "segment_id": "seg-2",
                "video_id": "video-1",
                "score": 0.7,
                "reason": "",
                "evidence": [],
            },
        ],
    )

    assert reflection.passed is False
    assert "missing_timestamp" in reflection.issues
    assert "missing_evidence" in reflection.issues
    assert "missing_reason" in reflection.issues


def test_reflection_fails_when_answer_mentions_only_segment_id():
    reflection = validate_grounding(
        final_answer="seg-1",
        results=[
            {
                "segment_id": "seg-1",
                "video_id": "video-1",
                "start_time": 1.0,
                "end_time": 3.0,
                "score": 0.8,
                "reason": "tags matched the query",
                "evidence": [{"evidence_type": "tag", "text": "热血", "start_time": 1.0}],
            }
        ],
    )

    assert reflection.passed is False
    assert "incomplete_answer" in reflection.issues


def test_reflection_passes_with_timestamp_evidence_reason_and_final_answer():
    reflection = validate_grounding(
        final_answer="Found segment seg-1 at 1.0-3.0s because tags matched the query with evidence 热血.",
        results=[
            {
                "segment_id": "seg-1",
                "video_id": "video-1",
                "start_time": 1.0,
                "end_time": 3.0,
                "score": 0.8,
                "reason": "tags matched the query",
                "evidence": [{"evidence_type": "tag", "text": "热血", "start_time": 1.0}],
            }
        ],
    )

    assert reflection.passed is True
    assert reflection.issues == []


def _segment(segment_id: str) -> MediaSegment:
    return MediaSegment(
        segment_id=segment_id,
        video_id="video-1",
        user_id="user-1",
        start_time=1.0,
        end_time=3.0,
        asr_transcript="热血 卡点 高能",
        tags=["热血", "卡点"],
        motion_score=0.9,
        highlight_score=0.88,
        evidence=[
            SegmentEvidence(
                evidence_type="asr",
                text="热血 卡点 高能",
                start_time=1.0,
                end_time=3.0,
                confidence=0.9,
            )
        ],
    )
