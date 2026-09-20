from __future__ import annotations

from camcat.agent.graph import CamCatGraph, CamCatState
from camcat.domain.project import Canvas, EditingProjectV2, MediaSourceRef


class CommandLlm:
    def json_completion(self, *, system: str, user: str):
        assert "RFC6902" in user
        return {
            "commands": [
                {
                    "type": "add_track",
                    "track": {
                        "type": "video",
                        "track_id": "main",
                        "name": "Main",
                        "segments": [],
                    },
                },
                {
                    "type": "insert_segment",
                    "track_id": "main",
                    "segment": {
                        "type": "video",
                        "segment_id": "segment-1",
                        "source_id": "source-1",
                        "timeline_start_us": 0,
                        "timeline_duration_us": 1_000_000,
                        "source_start_us": 0,
                        "source_duration_us": 1_000_000,
                    },
                },
            ],
            "summary": "typed commands",
        }


def test_agent_generates_simulates_and_validates_only_typed_delta_commands() -> None:
    project = EditingProjectV2(
        project_id="p",
        goal="g",
        title="t",
        canvas=Canvas(width=1920, height=1080, fps_num=30, fps_den=1),
        sources=[
            MediaSourceRef(
                source_id="source-1",
                origin="user_upload",
                storage_key="temporary/source.mp4",
                retention_class="transient_4h",
            )
        ],
    )
    graph = CamCatGraph(llm=CommandLlm(), retrieval=object())  # type: ignore[arg-type]
    state = CamCatState(
        query_text="make it concise",
        intent={"aspect_ratio": "16:9", "external_material_ratio_limit": 0.25},
        current_document=project.model_dump(mode="json", by_alias=True),
        source_materials=[
            {
                "media_id": "source-1",
                "start_time": 0,
                "end_time": 1,
                "description_text": "user footage",
            }
        ],
        ranked_materials=[],
    )

    planned = graph.generate_commands(state)
    command_types = [item["type"] for item in planned["domain_commands"]]
    assert command_types == ["update_canvas", "add_track", "insert_segment"]
    assert "operations" not in planned
    with_subtitles = graph.generate_subtitles(
        CamCatState(
            **state,
            domain_commands=planned["domain_commands"],
            simulated_document=planned["simulated_document"],
        )
    )
    validated = graph.validate_project(
        CamCatState(
            **state,
            domain_commands=with_subtitles["domain_commands"],
            simulated_document=with_subtitles["simulated_document"],
        )
    )
    assert validated["simulated_document"]["schema"] == "camcat-editing-project/v2"
