from __future__ import annotations

import json
import time
from typing import Any, Literal, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from camcat.agent.persistence import StatePersistenceService
from camcat.agent.scope import needs_material_retrieval
from camcat.domain.state_patch import VersionedState, apply_versioned_patch
from camcat.editing.policies import (
    choose_aspect_ratio,
    enforce_timeline_policy,
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
    edit_plan: list[dict[str, Any]]
    subtitles: list[dict[str, Any]]
    patch_operations: list[dict[str, Any]]
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
        graph.add_node("generate_edit_plan", self._traced("generate_edit_plan", self.generate_plan))
        graph.add_node(
            "generate_subtitles", self._traced("generate_subtitles", self.generate_subtitles)
        )
        graph.add_node("validate_patch", self._traced("validate_patch", self.validate_patch))
        graph.add_node("lightweight_edit", self._traced("lightweight_edit", self.lightweight_edit))
        graph.add_node("persistence", self._traced("persistence", self.persist))
        graph.add_edge(START, "understand_requirement")
        graph.add_conditional_edges(
            "understand_requirement",
            self._route_after_understanding,
            {"retrieve": "plan_query", "lightweight": "lightweight_edit"},
        )
        graph.add_edge("plan_query", "retrieve_material")
        graph.add_conditional_edges(
            "retrieve_material",
            lambda state: state.get("mode", "search"),
            {"search": END, "edit": "generate_edit_plan"},
        )
        graph.add_edge("generate_edit_plan", "generate_subtitles")
        graph.add_edge("generate_subtitles", "validate_patch")
        graph.add_edge("validate_patch", "persistence")
        graph.add_edge("lightweight_edit", "persistence")
        graph.add_edge("persistence", END)
        self.compiled = graph.compile()

    def invoke(self, state: CamCatState) -> CamCatState:
        initial: CamCatState = {
            **state,
            "route_sequence": [],
            "node_trace": [],
            "explicit_filters": state.get("explicit_filters", {}),
        }
        return cast(CamCatState, self.compiled.invoke(initial))

    def stream(self, state: CamCatState) -> Any:
        initial: CamCatState = {
            **state,
            "route_sequence": [],
            "node_trace": [],
            "explicit_filters": state.get("explicit_filters", {}),
        }
        return self.compiled.stream(initial, stream_mode="values")

    def understand(self, state: CamCatState) -> dict[str, Any]:
        result = self.llm.json_completion(
            system=(
                "You are CamCat's requirement-understanding node. Return strict JSON with "
                "search_query, target_duration_seconds, style, event_type, tags, platform, "
                "story_arc, pacing, and response_summary. User footage is always the primary story."
            ),
            user=state.get("query_text", "用参考图片寻找相似素材"),
        )
        source_media = state.get("current_document", {}).get("source_media", [])
        first_media = source_media[0] if source_media else {}
        ratio = choose_aspect_ratio(
            state.get("query_text", ""),
            int(first_media.get("width") or 0),
            int(first_media.get("height") or 0),
        )
        result["aspect_ratio"] = ratio
        result["external_material_ratio_limit"] = explicit_external_ratio(
            state.get("query_text", "")
        )
        return {
            "intent": result,
            "final_answer": str(result.get("response_summary", "已理解需求。")),
        }

    @staticmethod
    def _route_after_understanding(state: CamCatState) -> str:
        if state.get("mode", "search") == "search":
            return "retrieve"
        return (
            "retrieve" if needs_material_retrieval(state.get("query_text", "")) else "lightweight"
        )

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
        query_text = str(
            state.get("intent", {}).get("search_query") or state.get("query_text") or ""
        )
        materials = self.retrieval.search(
            query_text=query_text or None,
            query_image_base64=state.get("query_image_base64"),
            filters=state.get("filters", {}),
            top_k=int(state.get("top_k", 8)),
        )
        serialized = [
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
        answer = state.get("final_answer", "")
        source_materials = prepare_source_candidates(
            state.get("current_document", {}).get("source_segments", [])
        )
        return {
            "ranked_materials": serialized,
            "source_materials": source_materials,
            "final_answer": f"{answer} 已召回并重排 {len(serialized)} 个候选片段。",
        }

    def generate_plan(self, state: CamCatState) -> dict[str, Any]:
        source_materials = [
            {
                "segment_id": item["segment_id"],
                "origin": "source",
                "start_time": item["start_time"],
                "end_time": item["end_time"],
                "caption": item.get("description_text", ""),
                "quality_score": item.get("quality_score", 0.5),
                "storage_key": item["storage_key"],
                "media_id": item["media_id"],
                "segment_start": item["start_time"],
                "transcript_cues": item.get("transcript_cues", []),
            }
            for item in state.get("source_materials", [])
        ]
        library_materials = [
            {
                "segment_id": item["segment_id"],
                "origin": "library",
                "start_time": item["entity"]["start_time"],
                "end_time": item["entity"]["end_time"],
                "caption": item["entity"].get("description_text", ""),
                "score": item["reranker_score"],
            }
            for item in state["ranked_materials"]
        ]
        compact_materials = [*source_materials, *library_materials]
        if not source_materials:
            raise ValueError("剪辑任务缺少用户原片，请重新上传")
        result = self.llm.json_completion(
            system=(
                "You are CamCat's professional social-video edit-plan node. Select only supplied "
                "segment_id values. Return JSON with title, summary and clips. Each clip has "
                "segment_id, source_start, source_end, reason and transition. Build a coherent "
                "hook-development-payoff arc, remove repetition, prefer high-quality user footage, "
                "and use library B-roll only where it materially improves the story. User footage "
                "must be primary and library duration must obey external_material_ratio_limit."
            ),
            user=json.dumps(
                {
                    "intent": state["intent"],
                    "automatic_operations": [
                        "shot_deduplication",
                        "quality_scoring",
                        "rhythm_reorder",
                        "subtitles",
                        "transitions",
                        "loudness_normalization",
                        "basic_color_grade",
                        "platform_safe_area",
                    ],
                    "materials": compact_materials,
                },
                ensure_ascii=False,
            ),
        )
        allowed = {item["segment_id"]: item for item in compact_materials}
        clips: list[dict[str, Any]] = []
        for index, proposed in enumerate(result.get("clips", [])):
            segment_id = str(proposed.get("segment_id", ""))
            source = allowed.get(segment_id)
            if source is None:
                raise ValueError(f"edit-plan model selected unknown segment {segment_id}")
            start = max(
                float(source["start_time"]),
                float(proposed.get("source_start", source["start_time"])),
            )
            end = min(
                float(source["end_time"]), float(proposed.get("source_end", source["end_time"]))
            )
            if end <= start:
                raise ValueError("edit-plan model returned an invalid source range")
            clips.append(
                {
                    "clip_id": f"clip-{index + 1}",
                    "segment_id": segment_id,
                    "origin": source["origin"],
                    "storage_key": source.get("storage_key"),
                    "media_id": source.get("media_id"),
                    "segment_start": source.get("segment_start"),
                    "transcript_cues": source.get("transcript_cues", []),
                    "source_start": start,
                    "source_end": end,
                    "reason": str(proposed.get("reason", "语义匹配素材")),
                    "transition": str(proposed.get("transition", "fade")),
                }
            )
        if not any(item["origin"] == "source" for item in clips):
            best_source = max(source_materials, key=lambda item: float(item["quality_score"]))
            clips.insert(
                0,
                {
                    "clip_id": "clip-source-primary",
                    "segment_id": best_source["segment_id"],
                    "origin": "source",
                    "storage_key": best_source["storage_key"],
                    "media_id": best_source["media_id"],
                    "source_start": best_source["start_time"],
                    "source_end": best_source["end_time"],
                    "reason": "保证用户原片作为叙事主体",
                    "transition": "fade",
                },
            )
        if not clips:
            raise ValueError("edit-plan model returned no clips")
        clips = enforce_timeline_policy(
            clips,
            external_ratio_limit=float(state["intent"].get("external_material_ratio_limit", 0.25)),
        )
        return {"edit_plan": clips, "final_answer": str(result.get("summary", "剪辑计划已生成。"))}

    def generate_subtitles(self, state: CamCatState) -> dict[str, Any]:
        duration = float(state["edit_plan"][-1]["output_end"])
        aligned = self._aligned_transcript_subtitles(state["edit_plan"])
        if aligned:
            return {"subtitles": aligned}
        result = self.llm.json_completion(
            system=(
                "You are CamCat's subtitle node. Return JSON with subtitles. Each item has text, "
                "start and end seconds. Keep every cue within the supplied duration, ordered, "
                "concise, "
                "and suitable for a short-form video."
            ),
            user=json.dumps(
                {"intent": state["intent"], "duration": duration, "clips": state["edit_plan"]},
                ensure_ascii=False,
            ),
        )
        subtitles: list[dict[str, Any]] = []
        subtitle_items = result.get("subtitles", result.get("items", []))
        for index, item in enumerate(subtitle_items):
            start = max(0.0, float(item["start"]))
            end = min(duration, float(item["end"]))
            if end <= start:
                raise ValueError("subtitle model returned an invalid cue")
            subtitles.append(
                {
                    "subtitle_id": f"subtitle-{index + 1}",
                    "text": str(item["text"]).strip(),
                    "start": start,
                    "end": end,
                    "style": "default",
                }
            )
        return {"subtitles": subtitles}

    @staticmethod
    def _aligned_transcript_subtitles(edit_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
        subtitles: list[dict[str, Any]] = []
        for clip in edit_plan:
            segment_start = float(clip.get("segment_start") or clip["source_start"])
            source_start = float(clip["source_start"])
            source_end = float(clip["source_end"])
            output_start = float(clip["output_start"])
            for cue in clip.get("transcript_cues", []):
                cue_start = segment_start + float(cue.get("start", 0))
                cue_end = segment_start + float(cue.get("end", 0))
                start = max(source_start, cue_start)
                end = min(source_end, cue_end)
                text = str(cue.get("text") or "").strip()
                if text and end > start:
                    subtitles.append(
                        {
                            "subtitle_id": f"subtitle-{len(subtitles) + 1}",
                            "text": text,
                            "start": output_start + start - source_start,
                            "end": output_start + end - source_start,
                            "style": "default",
                        }
                    )
        return subtitles

    def lightweight_edit(self, state: CamCatState) -> dict[str, Any]:
        result = self.llm.json_completion(
            system=(
                "You are CamCat's metadata-only editing node. Never change clips. Return strict "
                "JSON containing only a title and/or subtitles requested by the user. Subtitle "
                "items require text, start and end and must fit the current duration."
            ),
            user=json.dumps(
                {
                    "instruction": state.get("query_text", ""),
                    "current_title": state.get("current_document", {}).get("title"),
                    "current_subtitles": state.get("current_document", {}).get("subtitles", []),
                    "duration": state.get("current_document", {}).get("target_duration", 0),
                },
                ensure_ascii=False,
            ),
        )
        operations: list[dict[str, Any]] = []
        if isinstance(result.get("title"), str) and result["title"].strip():
            operations.append({"op": "replace", "path": "/title", "value": result["title"].strip()})
        if isinstance(result.get("subtitles"), list):
            subtitles = []
            for index, item in enumerate(result["subtitles"]):
                subtitles.append(
                    {
                        "subtitle_id": f"subtitle-{index + 1}",
                        "text": str(item["text"]).strip(),
                        "start": float(item["start"]),
                        "end": float(item["end"]),
                        "style": "default",
                    }
                )
            operations.append({"op": "replace", "path": "/subtitles", "value": subtitles})
        if not operations:
            raise ValueError("metadata-only edit returned no applicable title or subtitles")
        apply_versioned_patch(
            VersionedState("validation", int(state["base_version"]), state["current_document"]),
            base_version=int(state["base_version"]),
            operations=operations,
            actor="agent",
            reason="validate lightweight patch",
        )
        return {"patch_operations": operations, "ranked_materials": []}

    def validate_patch(self, state: CamCatState) -> dict[str, Any]:
        audio_library = state.get("current_document", {}).get("audio_library", [])
        audio_by_kind = {
            kind: [item for item in audio_library if item.get("kind") == kind]
            for kind in ("bgm", "ambient", "sfx")
        }
        operations: list[dict[str, Any]] = [
            {"op": "replace", "path": "/clips", "value": state["edit_plan"]},
            {"op": "replace", "path": "/subtitles", "value": state["subtitles"]},
            {
                "op": "replace",
                "path": "/settings/aspect_ratio",
                "value": state["intent"]["aspect_ratio"],
            },
            {
                "op": "replace",
                "path": "/settings/external_material_ratio_limit",
                "value": state["intent"]["external_material_ratio_limit"],
            },
            {
                "op": "add",
                "path": "/audio_plan",
                "value": {
                    "normalize_loudness": True,
                    "target_lufs": -14,
                    "duck_music_under_dialogue": True,
                    "bgm": audio_by_kind["bgm"][:1],
                    "ambient": audio_by_kind["ambient"][:1],
                    "sound_effects": audio_by_kind["sfx"][:1],
                },
            },
        ]
        operations.append(
            {
                "op": "replace",
                "path": "/target_duration",
                "value": float(state["edit_plan"][-1]["output_end"]),
            }
        )
        apply_versioned_patch(
            VersionedState("validation", int(state["base_version"]), state["current_document"]),
            base_version=int(state["base_version"]),
            operations=operations,
            actor="agent",
            reason="validate agent patch",
        )
        return {"patch_operations": operations}

    def persist(self, state: CamCatState) -> dict[str, Any]:
        if state.get("mode") != "edit":
            return {}
        version, document = self.persistence.persist(
            session_id=state["session_id"],
            owner_id=state["owner_id"],
            base_version=int(state["base_version"]),
            operations=state["patch_operations"],
            reason=state.get("persistence_reason") or state.get("query_text", "agent edit"),
        )
        return {"persisted_version": version, "persisted_document": document}

    @staticmethod
    def _traced(name: str, function: Any) -> Any:
        def wrapped(state: CamCatState) -> dict[str, Any]:
            started = time.perf_counter()
            try:
                result = function(state)
                status = "completed"
                return {
                    **result,
                    "node_trace": [
                        *state.get("node_trace", []),
                        {
                            "node_name": name,
                            "status": status,
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
