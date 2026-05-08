import hashlib

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from backend.app.domain.models import Video
from backend.app.media.mock_pipeline import generate_mock_media_segments
from backend.app.repositories.in_memory import InMemoryMediaRepository

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
