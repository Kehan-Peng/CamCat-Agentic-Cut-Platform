import hashlib
from dataclasses import replace

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from backend.app.domain.models import SearchQuery, Video
from backend.app.media.mock_pipeline import generate_mock_media_segments
from backend.app.repositories.in_memory import InMemoryMediaRepository
from backend.app.retrieval.local_index import LocalMediaIndex
from backend.app.retrieval.query_rewrite import rewrite_query
from backend.app.retrieval.rerank import rerank_results
from backend.app.suggestions.creative import (
    build_creative_suggestion,
    build_overall_suggestion,
)

router = APIRouter()
repository = InMemoryMediaRepository()


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
    index = LocalMediaIndex(user_segments)
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
