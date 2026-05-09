import hashlib
from uuid import uuid4
from dataclasses import replace

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from backend.app.agents.checkpoint import build_in_memory_checkpointer
from backend.app.agents.graph import build_agent_graph, invoke_agent_graph
from backend.app.agents.planner import SearchPlanner
from backend.app.agents.state import AgentState
from backend.app.domain.models import SearchQuery, Video
from backend.app.media.mock_pipeline import generate_mock_media_segments
from backend.app.repositories.in_memory import InMemoryMediaRepository
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.query_rewrite import rewrite_query
from backend.app.retrieval.rerank import rerank_results
from backend.app.suggestions.creative import (
    build_creative_suggestion,
    build_overall_suggestion,
)

router = APIRouter()
repository = InMemoryMediaRepository()
agent_checkpointer = build_in_memory_checkpointer()


@router.get("/health")
def health():
    return {"status": "ok", "service": "nova-backend"}


def _require_user_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header is required")
    return x_user_id


def _video_id_for(user_id: str, filename: str, content: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(user_id.encode("utf-8"))
    digest.update(b"\0")
    digest.update(filename.encode("utf-8"))
    digest.update(b"\0")
    digest.update(content)
    return f"video-{digest.hexdigest()[:12]}"


@router.post("/api/v1/videos")
async def upload_video(
    file: UploadFile = File(...),
    user_id: str = Depends(_require_user_id),
):
    content = await file.read()
    video_id = _video_id_for(user_id, file.filename or "upload", content)
    video = Video(
        video_id=video_id,
        user_id=user_id,
        filename=file.filename or "upload",
        storage_uri=f"mock://uploads/{user_id}/{video_id}/{file.filename or 'upload'}",
        status="uploaded",
    )

    segments = generate_mock_media_segments(video)
    searchable_video = video.model_copy(update={"status": "searchable"})
    repository.save_video(searchable_video)
    for segment in segments:
        repository.save_segment(segment)

    return {
        "video_id": searchable_video.video_id,
        "status": searchable_video.status,
        "filename": searchable_video.filename,
        "segment_count": len(segments),
    }


@router.get("/api/v1/videos/{video_id}")
def get_video(
    video_id: str,
    user_id: str = Depends(_require_user_id),
):
    video = repository.get_video(user_id=user_id, video_id=video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    return {
        **video.model_dump(),
        "segment_count": len(repository.list_segments(user_id, video_id)),
    }


@router.get("/api/v1/segments/{segment_id}")
def get_segment(
    segment_id: str,
    user_id: str = Depends(_require_user_id),
):
    segment = repository.get_segment(user_id=user_id, segment_id=segment_id)
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    return segment


@router.post("/api/v1/search")
def search_segments(
    payload: dict,
    user_id: str = Depends(_require_user_id),
):
    query_text = str(payload.get("query_text", "")).strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="query_text is required")

    top_k = int(payload.get("top_k", 5))
    search_query = SearchQuery(
        query_text=query_text,
        user_id=user_id,
        session_id=payload.get("session_id"),
        top_k=max(1, min(top_k, 20)),
        filters=payload.get("filters") or {},
    )
    query_rewrite = rewrite_query(query_text)

    user_segments = repository.list_segments_for_user(user_id)
    index = HybridRetriever(user_segments)
    candidate_query = search_query.model_copy(update={"top_k": len(user_segments) or 1})
    ranked_results = rerank_results(index.search(candidate_query))[: search_query.top_k]
    ranked_results = [
        replace(result, creative_suggestion=build_creative_suggestion(result))
        for result in ranked_results
    ]
    overall_suggestion = build_overall_suggestion(ranked_results)

    return {
        "query_rewrite": query_rewrite.model_dump(),
        "expanded_queries": query_rewrite.expanded_queries,
        "results": [result.to_response() for result in ranked_results],
        "answer": "已按本地片段证据和高光分排序。",
        "creative_suggestion": overall_suggestion.model_dump(),
    }


@router.post("/api/v1/search/agentic")
def agentic_search_segments(
    payload: dict,
    user_id: str = Depends(_require_user_id),
):
    query_text = str(payload.get("query_text", "")).strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="query_text is required")

    top_k = int(payload.get("top_k", 5))
    search_query = SearchQuery(
        query_text=query_text,
        user_id=user_id,
        session_id=payload.get("session_id"),
        top_k=max(1, min(top_k, 20)),
        filters=payload.get("filters") or {},
    )

    user_segments = repository.list_segments_for_user(user_id)
    graph_run_id = f"graph-{uuid4().hex}"
    thread_id = str(payload.get("thread_id") or search_query.session_id or graph_run_id)
    state = AgentState(
        graph_run_id=graph_run_id,
        thread_id=thread_id,
        user_id=user_id,
        session_id=search_query.session_id,
        query_text=search_query.query_text,
        scenario=search_query.scenario,
        top_k=search_query.top_k,
        filters=search_query.filters,
    )
    final_state = invoke_agent_graph(
        build_agent_graph(user_segments, checkpointer=agent_checkpointer),
        state,
    )
    creative_suggestion = _first_creative_suggestion(final_state.creative_suggestions)
    reranked_segments = _serialize_results(final_state.reranked_segments)

    return {
        "plan": SearchPlanner().plan(search_query).model_dump(),
        "rewritten_query": final_state.rewritten_query,
        "tool_trace": _compat_tool_trace(final_state.node_trace),
        "ranked_segments": reranked_segments,
        "reflection": final_state.reflection_result,
        "final_answer": final_state.final_answer,
        "creative_suggestion": creative_suggestion,
        "graph_run_id": final_state.graph_run_id,
        "thread_id": final_state.thread_id,
        "state_snapshot": _state_snapshot(final_state),
        "node_trace": final_state.node_trace,
        "retrieved_segments": _serialize_results(final_state.retrieved_segments),
        "reranked_segments": reranked_segments,
        "reflection_result": final_state.reflection_result,
        "creative_suggestions": final_state.creative_suggestions,
    }


def _serialize_results(results: list) -> list[dict]:
    return [result.to_response() if hasattr(result, "to_response") else result for result in results]


def _first_creative_suggestion(suggestions: list) -> dict | None:
    return suggestions[0] if suggestions else None


def _state_snapshot(state: AgentState) -> dict:
    snapshot = state.model_dump(exclude={"retrieved_segments", "reranked_segments"})
    snapshot["retrieved_segments"] = _serialize_results(state.retrieved_segments)
    snapshot["reranked_segments"] = _serialize_results(state.reranked_segments)
    return snapshot


def _compat_tool_trace(node_trace: list[dict]) -> list[dict]:
    tool_names = {
        "query_rewrite": "query_rewrite",
        "retrieval": "search",
        "rerank": "rerank",
        "creative_suggestion": "creative_suggestion",
        "reflection": "reflection",
    }
    return [
        {
            "tool_name": tool_names[entry["node_name"]],
            "input": None,
            "status": entry["status"],
            "output": {"error": entry["error"]} if entry["error"] else None,
        }
        for entry in node_trace
        if entry["node_name"] in tool_names
    ]
