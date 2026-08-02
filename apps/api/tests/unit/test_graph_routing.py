from __future__ import annotations

from typing import Any

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
            "subtitle_id": "subtitle-1",
            "text": "hello",
            "start": 0.25,
            "end": 0.75,
            "style": "default",
        }
    ]
