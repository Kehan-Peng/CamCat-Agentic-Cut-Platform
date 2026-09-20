from __future__ import annotations

import json
import time
from typing import Any, Literal, TypedDict, cast
from uuid import NAMESPACE_URL, uuid5

from langgraph.graph import END, START, StateGraph
from pydantic import TypeAdapter, ValidationError

from camcat.agent.persistence import StatePersistenceService
from camcat.agent.scope import editing_retrieval_filters
from camcat.domain.commands import (
    AddTrack,
    DomainEditCommand,
    InsertSegment,
    RegisterSource,
    UpdateCanvas,
)
from camcat.domain.project import (
    Canvas,
    EditingProjectV2,
    MediaSourceRef,
    TextSegment,
    TextTrack,
    VideoSegment,
    VideoTrack,
)
from camcat.domain.reducer import reduce_commands
from camcat.editing.policies import (
    choose_aspect_ratio,
    explicit_external_ratio,
    prepare_source_candidates,
)
from camcat.retrieval.service import RetrievalService
from camcat.services.providers import QwenChatClient


class CamCatState(TypedDict, total=False):
    mode: Literal["search", "edit"]
    query_text: str
    query_image_base64: str
    explicit_filters: dict[str, Any]
    top_k: int
    current_document: dict[str, Any]
    base_version: int
    intent: dict[str, Any]
    filters: dict[str, Any]
    ranked_materials: list[dict[str, Any]]
    source_materials: list[dict[str, Any]]
    domain_commands: list[dict[str, Any]]
    simulated_document: dict[str, Any]
    final_answer: str
    route_sequence: list[str]
    node_trace: list[dict[str, Any]]
    session_id: str
    owner_id: str
    persistence_reason: str
    persisted_version: int
    persisted_document: dict[str, Any]


class CamCatGraph:
    def __init__(
        self,
        *,
        llm: QwenChatClient,
        retrieval: RetrievalService,
        persistence: StatePersistenceService | None = None,
    ) -> None:
        self.llm = llm
        self.retrieval = retrieval
        self.persistence = persistence or StatePersistenceService()
        graph = StateGraph(CamCatState)
        graph.add_node(
            "understand_requirement", self._traced("understand_requirement", self.understand)
        )
        graph.add_node("plan_query", self._traced("plan_query", self.plan_query))
        graph.add_node("retrieve_material", self._traced("retrieve_material", self.retrieve))
        graph.add_node(
            "generate_edit_plan", self._traced("generate_edit_plan", self.generate_commands)
        )
        graph.add_node(
            "generate_subtitles", self._traced("generate_subtitles", self.generate_subtitles)
        )
        graph.add_node("validate_project", self._traced("validate_project", self.validate_project))
        graph.add_node("persistence", self._traced("persistence", self.persist))
        graph.add_edge(START, "understand_requirement")
        graph.add_edge("understand_requirement", "plan_query")
        graph.add_edge("plan_query", "retrieve_material")
        graph.add_conditional_edges(
            "retrieve_material",
            lambda state: state.get("mode", "search"),
            {"search": END, "edit": "generate_edit_plan"},
        )
        graph.add_edge("generate_edit_plan", "generate_subtitles")
        graph.add_edge("generate_subtitles", "validate_project")
        graph.add_edge("validate_project", "persistence")
        graph.add_edge("persistence", END)
        self.compiled = graph.compile()

    def invoke(self, state: CamCatState) -> CamCatState:
        return cast(CamCatState, self.compiled.invoke(self._initial(state)))

    def stream(self, state: CamCatState) -> Any:
        return self.compiled.stream(self._initial(state), stream_mode="values")

    @staticmethod
    def _initial(state: CamCatState) -> CamCatState:
        return {
            **state,
            "route_sequence": [],
            "node_trace": [],
            "explicit_filters": state.get("explicit_filters", {}),
        }

    def understand(self, state: CamCatState) -> dict[str, Any]:
        result = self.llm.json_completion(
            system=(
                "You are CamCat's requirement-understanding node. Return strict JSON with "
                "search_query, target_duration_seconds, style, event_type, tags, platform, "
                "story_arc, pacing, and response_summary. User footage is always primary."
            ),
            user=state.get("query_text", "用参考图片寻找相似素材"),
        )
        project_payload = state.get("current_document")
        source_media = (
            EditingProjectV2.model_validate(project_payload).metadata.get("source_media", [])
            if project_payload
            else []
        )
        first = source_media[0] if source_media else {}
        result["aspect_ratio"] = choose_aspect_ratio(
            state.get("query_text", ""), int(first.get("width") or 0), int(first.get("height") or 0)
        )
        result["external_material_ratio_limit"] = explicit_external_ratio(
            state.get("query_text", "")
        )
        return {
            "intent": result,
            "final_answer": str(result.get("response_summary", "已理解需求。")),
        }

    def plan_query(self, state: CamCatState) -> dict[str, Any]:
        intent = state["intent"]
        filters = dict(state.get("explicit_filters", {}))
        if intent.get("event_type"):
            filters.setdefault("event_type", str(intent["event_type"]))
        if isinstance(intent.get("tags"), list) and intent["tags"]:
            filters.setdefault("tags", [str(item) for item in intent["tags"]])
        return {
            "filters": filters,
            "route_sequence": ["dense", "bm25", "scalar", "business_fusion", "qwen_vl_rerank"],
        }

    def retrieve(self, state: CamCatState) -> dict[str, Any]:
        query = str(state.get("intent", {}).get("search_query") or state.get("query_text") or "")
        materials = self.retrieval.search(
            query_text=query or None,
            query_image_base64=state.get("query_image_base64"),
            filters=state.get("filters", {}),
            top_k=int(state.get("top_k", 8)),
        )
        ranked = [
            {
                "segment_id": item.segment_id,
                "score": item.score,
                "reranker_score": item.reranker_score,
                "entity": item.entity,
                "route_scores": item.route_scores,
                "route_ranks": item.route_ranks,
            }
            for item in materials
        ]
        source_segments = []
        if state.get("current_document"):
            project = EditingProjectV2.model_validate(state["current_document"])
            source_segments = cast(
                list[dict[str, Any]], project.metadata.get("source_segments", [])
            )
        sources = prepare_source_candidates(source_segments)
        return {
            "ranked_materials": ranked,
            "source_materials": sources,
            "final_answer": (
                f"{state.get('final_answer', '')} 已召回并重排 {len(ranked)} 个候选片段。"
            ),
        }

    def generate_commands(self, state: CamCatState) -> dict[str, Any]:
        project = EditingProjectV2.model_validate(state["current_document"])
        candidates, registry = self._candidate_registry(state, project)
        if not any(item["origin"] == "user_upload" for item in candidates):
            raise ValueError("剪辑任务缺少用户原片，请重新上传")
        canvas = _canvas_for_ratio(state["intent"].get("aspect_ratio", "16:9"), project.canvas)
        payload: dict[str, Any] = {
            "instruction": state.get("query_text", ""),
            "project": project.model_dump(mode="json", by_alias=True),
            "materials": candidates,
            "contract": {
                "time_unit": "integer microseconds",
                "allowed_commands": [
                    "add_track",
                    "remove_track",
                    "rename_track",
                    "insert_segment",
                    "move_segment",
                    "remove_segment",
                    "trim_segment",
                    "split_segment",
                    "replace_segment_media",
                    "set_segment_transform",
                    "update_text_segment",
                    "add_audio_segment",
                    "update_audio_segment",
                    "remove_audio_segment",
                    "set_transition",
                    "remove_transition",
                    "update_title",
                    "update_goal",
                ],
                "forbidden": ["RFC6902", "complete timeline replacement", "FFmpeg", "frames"],
            },
        }
        system = (
            "You are CamCat's domain-command planning node. Return strict JSON with a commands "
            "array matching the supplied command contract. Use only stable source_id values from "
            "materials, integer microseconds, and stable anchors; never return array indexes, "
            "patch "
            "paths, a whole replacement timeline, frames, or renderer instructions. For an empty "
            "project add one video track before inserting video segments. User-upload footage must "
            "remain the primary story and licensed-library duration must stay within the given "
            "limit."
        )
        parsed: list[DomainEditCommand] | None = None
        for attempt in range(2):
            result = self.llm.json_completion(
                system=system, user=json.dumps(payload, ensure_ascii=False)
            )
            try:
                parsed = _parse_commands(result.get("commands"))
                break
            except (ValidationError, ValueError) as exc:
                if attempt:
                    raise ValueError(
                        f"domain-command model failed validation after repair: {exc}"
                    ) from exc
                payload["validation_error"] = str(exc)
                payload["previous_output"] = result
        assert parsed is not None
        referenced = {
            command.segment.source_id
            for command in parsed
            if isinstance(command, InsertSegment) and isinstance(command.segment, VideoSegment)
        }
        existing_sources = {item.source_id for item in project.sources}
        registrations = [
            RegisterSource(source=registry[source_id])
            for source_id in sorted(referenced - existing_sources)
            if source_id in registry
        ]
        if referenced - existing_sources - set(registry):
            raise ValueError("domain commands reference a source outside the supplied material set")
        commands: list[DomainEditCommand] = [UpdateCanvas(canvas=canvas), *registrations, *parsed]
        reduced = reduce_commands(project, commands)
        self._validate_external_ratio(
            reduced.project, float(state["intent"].get("external_material_ratio_limit", 0.25))
        )
        return {
            "domain_commands": [item.model_dump(mode="json") for item in commands],
            "simulated_document": reduced.project.model_dump(mode="json", by_alias=True),
            "final_answer": str(result.get("summary", "剪辑命令已生成。")),
        }

    def generate_subtitles(self, state: CamCatState) -> dict[str, Any]:
        project = EditingProjectV2.model_validate(state["simulated_document"])
        commands = _parse_commands(state["domain_commands"])
        text_tracks = [item for item in project.timeline.tracks if isinstance(item, TextTrack)]
        if not text_tracks:
            track = TextTrack(track_id="text-captions", name="Captions")
            commands.append(AddTrack(track=track))
            text_track_id = track.track_id
        else:
            text_track_id = text_tracks[0].track_id
        metadata_segments = cast(list[dict[str, Any]], project.metadata.get("source_segments", []))
        by_source: dict[str, list[dict[str, Any]]] = {}
        for item in metadata_segments:
            by_source.setdefault(str(item.get("media_id")), []).append(item)
        added = 0
        for source_track in project.timeline.tracks:
            if not isinstance(source_track, VideoTrack):
                continue
            for segment in source_track.segments:
                for source_segment in by_source.get(segment.source_id, []):
                    base_us = round(float(source_segment.get("start_time", 0)) * 1_000_000)
                    for cue_index, cue in enumerate(source_segment.get("transcript_cues", [])):
                        cue_start = base_us + round(float(cue.get("start", 0)) * 1_000_000)
                        cue_end = base_us + round(float(cue.get("end", 0)) * 1_000_000)
                        start = max(segment.source_start_us, cue_start)
                        end = min(segment.source_start_us + segment.source_duration_us, cue_end)
                        text = str(cue.get("text") or "").strip()
                        if not text or end <= start:
                            continue
                        timeline_start = segment.timeline_start_us + round(
                            (start - segment.source_start_us) / segment.speed
                        )
                        duration = round((end - start) / segment.speed)
                        commands.append(
                            InsertSegment(
                                track_id=text_track_id,
                                segment=TextSegment(
                                    segment_id=str(
                                        uuid5(
                                            NAMESPACE_URL,
                                            f"camcat-text:{segment.segment_id}:{cue_index}:{start}:{end}",
                                        )
                                    ),
                                    start_us=timeline_start,
                                    duration_us=duration,
                                    text=text,
                                ),
                            )
                        )
                        added += 1
        reduced = reduce_commands(
            EditingProjectV2.model_validate(state["current_document"]), commands
        )
        return {
            "domain_commands": [item.model_dump(mode="json") for item in commands],
            "simulated_document": reduced.project.model_dump(mode="json", by_alias=True),
            "final_answer": f"{state.get('final_answer', '')} 已生成 {added} 条字幕。",
        }

    def validate_project(self, state: CamCatState) -> dict[str, Any]:
        commands = _parse_commands(state["domain_commands"])
        project = EditingProjectV2.model_validate(state["current_document"])
        reduced = reduce_commands(project, commands)
        expected = EditingProjectV2.model_validate(state["simulated_document"])
        if reduced.project != expected:
            raise ValueError("command simulation is nondeterministic")
        return {"simulated_document": reduced.project.model_dump(mode="json", by_alias=True)}

    def persist(self, state: CamCatState) -> dict[str, Any]:
        if state.get("mode") != "edit":
            return {}
        version, document = self.persistence.persist(
            session_id=state["session_id"],
            owner_id=state["owner_id"],
            base_version=int(state["base_version"]),
            commands=_parse_commands(state["domain_commands"]),
            reason=state.get("persistence_reason") or state.get("query_text", "agent edit"),
        )
        return {"persisted_version": version, "persisted_document": document}

    @staticmethod
    def _candidate_registry(
        state: CamCatState, project: EditingProjectV2
    ) -> tuple[list[dict[str, Any]], dict[str, MediaSourceRef]]:
        existing = {item.source_id: item for item in project.sources}
        candidates: list[dict[str, Any]] = []
        registry = dict(existing)
        for item in state.get("source_materials", []):
            source_id = str(item["media_id"])
            source = existing[source_id]
            candidates.append(
                {
                    "source_id": source_id,
                    "origin": "user_upload",
                    "source_start_us": round(float(item["start_time"]) * 1_000_000),
                    "source_duration_us": round(
                        (float(item["end_time"]) - float(item["start_time"])) * 1_000_000
                    ),
                    "description": item.get("description_text", ""),
                    "quality_score": item.get("quality_score", 0.5),
                }
            )
        for item in state.get("ranked_materials", []):
            entity = item["entity"]
            source_id = str(item["segment_id"])
            duration_us = round(
                (float(entity["end_time"]) - float(entity["start_time"])) * 1_000_000
            )
            source = MediaSourceRef(
                source_id=source_id,
                origin="licensed_library",
                storage_key=str(entity["storage_key"]),
                retention_class="library",
                metadata={
                    "license_name": entity.get("license_name"),
                    "source_url": entity.get("source_url"),
                },
            )
            registry[source_id] = source
            candidates.append(
                {
                    "source_id": source_id,
                    "origin": "licensed_library",
                    "source_start_us": 0,
                    "source_duration_us": duration_us,
                    "description": entity.get("description_text", ""),
                    "reranker_score": item["reranker_score"],
                }
            )
        return candidates, registry

    @staticmethod
    def _validate_external_ratio(project: EditingProjectV2, limit: float) -> None:
        origins = {item.source_id: item.origin for item in project.sources}
        videos = [
            segment
            for track in project.timeline.tracks
            if isinstance(track, VideoTrack)
            for segment in track.segments
        ]
        total = sum(item.timeline_duration_us for item in videos)
        external = sum(
            item.timeline_duration_us
            for item in videos
            if origins[item.source_id] == "licensed_library"
        )
        if not total or not any(origins[item.source_id] == "user_upload" for item in videos):
            raise ValueError("user footage must remain the primary story")
        if external / total > limit + 1e-9:
            raise ValueError("licensed-library duration exceeds the requested ratio limit")

    @staticmethod
    def _traced(name: str, function: Any) -> Any:
        def wrapped(state: CamCatState) -> dict[str, Any]:
            started = time.perf_counter()
            try:
                result = function(state)
                return {
                    **result,
                    "node_trace": [
                        *state.get("node_trace", []),
                        {
                            "node_name": name,
                            "status": "completed",
                            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        },
                    ],
                }
            except Exception:
                state.setdefault("node_trace", []).append(
                    {
                        "node_name": name,
                        "status": "failed",
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                )
                raise

        return wrapped


def _parse_commands(value: Any) -> list[DomainEditCommand]:
    if not isinstance(value, list) or not value:
        raise ValueError("domain command output must contain a nonempty commands array")
    return TypeAdapter(list[DomainEditCommand]).validate_python(value)


def _canvas_for_ratio(value: Any, current: Canvas) -> Canvas:
    dimensions = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "3:4": (1080, 1440),
        "4:3": (1440, 1080),
        "1:1": (1080, 1080),
    }
    width, height = dimensions.get(str(value), (current.width, current.height))
    return Canvas(
        width=width,
        height=height,
        fps_num=current.fps_num,
        fps_den=current.fps_den,
    )


__all__ = ["CamCatGraph", "CamCatState", "editing_retrieval_filters"]
