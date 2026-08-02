from __future__ import annotations

from typing import Any

CANONICAL_EMBEDDING_MODEL = "Qwen/Qwen3-VL-Embedding-8B"
CANONICAL_RERANKER_MODEL = "Qwen/Qwen3-VL-Reranker-8B"
BAILIAN_EMBEDDING_MODEL = "qwen3-vl-embedding"
BAILIAN_RERANKER_MODEL = "qwen3-vl-rerank"


def build_embedding_payload(
    *,
    canonical_model: str,
    dimensions: int,
    text: str | None = None,
    image_data_uri: str | None = None,
    video_url: str | None = None,
    instruction: str | None = None,
    fps: float | None = None,
) -> dict[str, Any]:
    """Translate the strict CamCat embedding contract to Bailian DashScope JSON."""

    if canonical_model != CANONICAL_EMBEDDING_MODEL:
        raise ValueError("canonical embedding model is required")
    if dimensions != 2048:
        raise ValueError("CamCat requires a 2048-dimensional embedding")
    contents: list[dict[str, str]] = []
    if text and text.strip():
        contents.append({"text": text.strip()})
    if image_data_uri:
        contents.append({"image": image_data_uri})
    if video_url:
        contents.append({"video": video_url})
    if not contents:
        raise ValueError("at least one text, image or video input is required")
    parameters: dict[str, Any] = {"dimension": 2048, "enable_fusion": True}
    if fps is not None:
        if not 0 <= fps <= 1:
            raise ValueError("Bailian video fps must be between 0 and 1")
        parameters["fps"] = fps
    if instruction and instruction.strip():
        parameters["instruct"] = instruction.strip()
    return {
        "model": BAILIAN_EMBEDDING_MODEL,
        "input": {"contents": contents},
        "parameters": parameters,
    }


def extract_embedding_response(payload: dict[str, Any], *, dimensions: int) -> list[float]:
    output = payload.get("output")
    embeddings = output.get("embeddings") if isinstance(output, dict) else None
    if not isinstance(embeddings, list) or len(embeddings) != 1:
        raise ValueError("Bailian must return exactly one fused embedding")
    item = embeddings[0]
    raw = item.get("embedding") if isinstance(item, dict) else None
    if not isinstance(raw, list):
        raise ValueError("Bailian embedding response is missing the vector")
    try:
        vector = [float(value) for value in raw]
    except (TypeError, ValueError) as exc:
        raise ValueError("Bailian embedding vector contains non-numeric values") from exc
    if len(vector) != dimensions:
        raise ValueError(
            f"Bailian embedding dimension mismatch: expected {dimensions}, got {len(vector)}"
        )
    if not any(value != 0 for value in vector):
        raise ValueError("Bailian returned an all-zero embedding")
    return vector


def build_rerank_payload(
    *,
    canonical_model: str,
    query: dict[str, Any],
    documents: list[dict[str, Any]],
    instruction: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Translate rerank inputs while keeping metadata as an explicit sidecar."""

    if canonical_model != CANONICAL_RERANKER_MODEL:
        raise ValueError("canonical reranker model is required")
    if not documents:
        raise ValueError("at least one reranker document is required")
    upstream_query = _modal_content(query, allow_video=False)
    if not upstream_query:
        raise ValueError("reranker query requires text or image")
    if len(upstream_query) != 1:
        raise ValueError("Bailian reranker requires exactly one query modality")
    upstream_documents: list[dict[str, str]] = []
    metadata: list[dict[str, Any]] = []
    for document in documents:
        content = _modal_content(document, allow_video=True)
        if not content:
            raise ValueError("reranker documents require text, image or video")
        if len(content) != 1:
            raise ValueError("Bailian reranker requires exactly one modality per document")
        upstream_documents.append(content)
        raw_metadata = document.get("metadata", {})
        if raw_metadata is None:
            raw_metadata = {}
        if not isinstance(raw_metadata, dict):
            raise ValueError("reranker document metadata must be an object")
        metadata.append(dict(raw_metadata))
    parameters: dict[str, Any] = {
        "return_documents": False,
        "top_n": len(upstream_documents),
    }
    if instruction and instruction.strip():
        parameters["instruct"] = instruction.strip()
    return (
        {
            "model": BAILIAN_RERANKER_MODEL,
            "input": {"query": upstream_query, "documents": upstream_documents},
            "parameters": parameters,
        },
        metadata,
    )


def extract_rerank_response(
    payload: dict[str, Any], *, document_count: int
) -> list[dict[str, float | int]]:
    output = payload.get("output")
    results = output.get("results") if isinstance(output, dict) else None
    if not isinstance(results, list) or len(results) != document_count:
        raise ValueError("Bailian reranker returned an invalid result count")
    normalized: list[dict[str, float | int]] = []
    seen: set[int] = set()
    for item in results:
        if not isinstance(item, dict):
            raise ValueError("Bailian reranker returned an invalid result")
        try:
            index = int(item["index"])
            score = float(item["relevance_score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Bailian reranker result is missing index or score") from exc
        if index < 0 or index >= document_count or index in seen:
            raise ValueError("Bailian reranker returned invalid or duplicate indices")
        seen.add(index)
        normalized.append({"index": index, "relevance_score": score})
    return normalized


def _modal_content(value: dict[str, Any], *, allow_video: bool) -> dict[str, str]:
    content: dict[str, str] = {}
    text = value.get("text")
    if isinstance(text, str) and text.strip():
        content["text"] = text.strip()
    image = value.get("image_base64", value.get("image"))
    if isinstance(image, str) and image:
        content["image"] = image
    if allow_video:
        video = value.get("video_url", value.get("video"))
        if isinstance(video, str) and video:
            content["video"] = video
    return content
