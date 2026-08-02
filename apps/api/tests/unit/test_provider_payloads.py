from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from camcat.config import Settings
from camcat.services.providers import (
    ProviderError,
    QwenEmbeddingClient,
    QwenRerankerClient,
    SegmentSemantics,
    parse_structured_content,
)
from pydantic import SecretStr, ValidationError


def settings() -> Settings:
    return Settings.model_construct(
        embedding_base_url="https://provider.test",
        embedding_api_key=SecretStr("secret"),
        embedding_model="Qwen/Qwen3-VL-Embedding-8B",
        embedding_dimension=2048,
        reranker_base_url="https://provider.test",
        reranker_api_key=SecretStr("secret"),
        reranker_model="Qwen/Qwen3-VL-Reranker-8B",
        llm_base_url="https://provider.test",
        llm_api_key=SecretStr("secret"),
        asr_base_url="https://provider.test",
        asr_api_key=SecretStr("secret"),
        provider_timeout_seconds=10,
        provider_max_retries=0,
        embedding_video_fps=1.0,
        embedding_video_max_frames=64,
    )


def test_structured_content_accepts_json_object() -> None:
    assert parse_structured_content('{"summary":"ok"}') == {"summary": "ok"}


def test_structured_content_normalizes_top_level_model_array() -> None:
    assert parse_structured_content('[{"text":"第一幕","start":0,"end":1}]') == {
        "items": [{"text": "第一幕", "start": 0, "end": 1}]
    }


def test_structured_content_removes_markdown_json_fence() -> None:
    assert parse_structured_content('```json\n{"clips":[]}\n```') == {"clips": []}


def test_embedding_contract_uploads_original_video_as_multipart(tmp_path: Path) -> None:
    video = tmp_path / "source.mp4"
    video.write_bytes(b"real-video-bytes")
    client = QwenEmbeddingClient(settings())
    captured: dict[str, Any] = {}

    def request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(method=method, path=path, **kwargs)
        captured["video_bytes"] = kwargs["files"]["video"][1].read()
        return {"data": [{"embedding": [0.5] * 2048}]}

    client.request = request  # type: ignore[method-assign]
    vector = client.embed_video(video, text="sunset")

    assert vector == [0.5] * 2048
    assert captured["path"] == "/v1/embeddings"
    assert "json" not in captured
    assert captured["data"] == {
        "model": "Qwen/Qwen3-VL-Embedding-8B",
        "dimensions": "2048",
        "text": "sunset",
        "fps": "1.0",
        "max_frames": "64",
    }
    filename, _stream, media_type = captured["files"]["video"]
    assert filename == "source.mp4"
    assert media_type == "video/mp4"
    assert captured["video_bytes"] == b"real-video-bytes"


def test_embedding_contract_rejects_multiple_vectors_instead_of_averaging() -> None:
    client = QwenEmbeddingClient(settings())
    with pytest.raises(ProviderError, match="exactly one embedding"):
        client._extract({"data": [{"embedding": [1.0] * 2048}, {"embedding": [2.0] * 2048}]})


def test_mixed_rerank_preserves_text_image_and_document_metadata() -> None:
    client = QwenRerankerClient(settings())
    captured: dict[str, Any] = {}

    def request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        captured.update(method=method, path=path, **kwargs)
        return {"results": [{"index": 0, "relevance_score": 0.9}]}

    client.request = request  # type: ignore[method-assign]
    query = {"text": "sunset", "image_base64": "data:image/jpeg;base64,YQ=="}
    documents = [{"text": "beach", "metadata": {"license": "CC0", "tags": ["sea"]}}]

    assert client.rerank(query, documents) == [0.9]
    assert captured["path"] == "/v1/rerank"
    assert captured["json"]["query"] == query
    assert captured["json"]["documents"] == documents


def test_healthcheck_uses_provider_health_contract() -> None:
    client = QwenEmbeddingClient(settings())
    calls: list[tuple[str, str]] = []
    client.request = lambda method, path, **_kwargs: calls.append((method, path)) or {}  # type: ignore[method-assign]

    client.healthcheck()

    assert calls == [("GET", "/health")]


def test_segment_semantics_rejects_unbounded_risk_and_empty_description() -> None:
    with pytest.raises(ValidationError):
        SegmentSemantics.model_validate(
            {
                "description": "",
                "scene": "shore",
                "actions": [],
                "people": [],
                "composition": "wide",
                "tags": [],
                "event_type": "travel",
                "risk_score": 2,
                "risk_labels": [],
            }
        )
