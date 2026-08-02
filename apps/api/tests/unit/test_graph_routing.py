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
