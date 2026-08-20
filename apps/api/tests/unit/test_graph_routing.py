from __future__ import annotations

import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest
from camcat.agent.graph import CamCatGraph, CamCatState


class FakeLlm:
    def __init__(self) -> None:
        self.calls = 0

    def json_completion(self, *, system: str, user: str) -> dict[str, Any]:
        self.calls += 1
        if "requirement-understanding" in system:
            return {"search_query": "unused", "response_summary": "ok"}
        return {"title": "夏日记忆"}


class FailingRetrieval:
    def search(self, **_kwargs: Any) -> list[Any]:
        raise AssertionError("lightweight edit must not retrieve")


class RecordingPersistence:
    def __init__(self) -> None:
        self.operations: list[dict[str, Any]] = []

    def persist(self, **kwargs: Any) -> tuple[int, dict[str, Any]]:
        self.operations = kwargs["operations"]
        return 2, {**kwargs, "title": "夏日记忆"}


def test_lightweight_edit_skips_retrieval_and_persists_inside_graph() -> None:
    persistence = RecordingPersistence()
    graph = CamCatGraph(  # type: ignore[arg-type]
        llm=FakeLlm(), retrieval=FailingRetrieval(), persistence=persistence
    )
    result = graph.invoke(
        CamCatState(
            mode="edit",
            query_text="把标题改成夏日记忆",
            current_document={
                "title": "旧标题",
                "clips": [],
                "subtitles": [],
                "audio_plan": {"bgm": [], "ambient": [], "sound_effects": []},
            },
            base_version=1,
            session_id="session-id",
            owner_id="owner-id",
            persistence_reason="rename",
        )
    )

    assert persistence.operations == [{"op": "replace", "path": "/title", "value": "夏日记忆"}]
    assert result["persisted_version"] == 2
    assert [item["node_name"] for item in result["node_trace"]] == [
        "understand_requirement",
        "lightweight_edit",
        "persistence",
    ]


class LibraryOnlyPlanLlm:
    def json_completion(self, *, system: str, user: str) -> dict[str, Any]:
        return {
            "clips": [
                {
                    "segment_id": "library-1",
                    "source_start": 0,
                    "source_end": 1,
                }
            ]
        }


def test_plan_repair_is_bounded_and_receives_current_timeline() -> None:
    class InvalidPlanLlm:
        def __init__(self):
            self.inputs = []

        def json_completion(self, *, system, user):
            self.inputs.append(json.loads(user))
            return {"clips": [{"segment_id": "missing"}]}

    llm = InvalidPlanLlm()
    graph = CamCatGraph(llm=llm, retrieval=FailingRetrieval())
    with pytest.raises(ValueError, match="failed deterministic validation"):
        graph.generate_plan(
            CamCatState(
                intent={},
                query_text="缩短开头，保留结尾",
                current_document={"clips": [{"clip_id": "previous"}]},
                source_materials=[
                    {
                        "segment_id": "real",
                        "start_time": 0,
                        "end_time": 4,
                        "storage_key": "source",
                        "media_id": "media",
                    }
                ],
                ranked_materials=[],
            )
        )
    assert len(llm.inputs) == 2
    assert llm.inputs[0]["instruction"] == "缩短开头，保留结尾"
    assert llm.inputs[0]["current_clips"] == [{"clip_id": "previous"}]
    assert llm.inputs[1]["validation_error"]


def test_trimmed_clip_preserves_zero_segment_origin_for_subtitles() -> None:
    subtitles = CamCatGraph._aligned_transcript_subtitles(
        [
            {
                "clip_id": "clip-source",
                "media_id": "media",
                "segment_start": 0,
                "source_start": 2,
                "source_end": 4,
                "transcript_cues": [{"start": 2.5, "end": 3, "text": "原声"}],
            }
        ]
    )
    assert subtitles[0]["source_start"] == 2.5
    assert subtitles[0]["source_end"] == 3


def test_corrected_model_plan_succeeds_without_inventing_material() -> None:
    class RepairingLlm:
        calls = 0

        def json_completion(self, *, system, user):
            self.calls += 1
            return {"clips": [{"segment_id": "unknown" if self.calls == 1 else "real"}]}

    llm = RepairingLlm()
    graph = CamCatGraph(llm=llm, retrieval=FailingRetrieval())
    result = graph.generate_plan(
        CamCatState(
            intent={},
            source_materials=[
                {
                    "segment_id": "real",
                    "start_time": 0,
                    "end_time": 4,
                    "storage_key": "temporary/source.mp4",
                    "media_id": "media",
                }
            ],
            ranked_materials=[],
        )
    )
    assert llm.calls == 2
    assert [clip["segment_id"] for clip in result["edit_plan"]] == ["real"]
    assert result["edit_plan"][0]["source_end"] == 4


def test_source_fallback_keeps_asr_cues_for_timestamp_aligned_subtitles() -> None:
    graph = CamCatGraph(  # type: ignore[arg-type]
        llm=LibraryOnlyPlanLlm(), retrieval=FailingRetrieval()
    )
    cues = [{"text": "hello", "start": 0.25, "end": 0.75}]
    result = graph.generate_plan(
        CamCatState(
            intent={"external_material_ratio_limit": 0.25},
            source_materials=[
                {
                    "segment_id": "source-1",
                    "start_time": 2.0,
                    "end_time": 4.0,
                    "quality_score": 0.9,
                    "description_text": "source",
                    "storage_key": "temporary/source.mp4",
                    "media_id": "media-1",
                    "transcript_cues": cues,
                }
            ],
            ranked_materials=[
                {
                    "segment_id": "library-1",
                    "reranker_score": 1.0,
                    "entity": {
                        "start_time": 0.0,
                        "end_time": 1.0,
                        "description_text": "library",
                    },
                }
            ],
        )
    )

    source_clip = result["edit_plan"][0]
    assert source_clip["segment_start"] == 2.0
    assert source_clip["transcript_cues"] == cues
    assert graph._aligned_transcript_subtitles(result["edit_plan"]) == [
        {
            "subtitle_id": str(
                uuid5(
                    NAMESPACE_URL,
                    f"camcat-subtitle:{source_clip['clip_id']}:2.250000:2.750000",
                )
            ),
            "text": "hello",
            "clip_id": source_clip["clip_id"],
            "source_id": "media-1",
            "source_start": 2.25,
            "source_end": 2.75,
            "style": "default",
        }
    ]
