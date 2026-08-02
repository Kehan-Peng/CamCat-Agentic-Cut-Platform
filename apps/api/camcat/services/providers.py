from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator

from camcat.config import Settings


class ProviderError(RuntimeError):
    pass


class _ProviderClient:
    def __init__(self, *, base_url: str, api_key: str, settings: Settings) -> None:
        self.settings = settings
        self.base_url = base_url.rstrip("/")
        self.max_retries = settings.provider_max_retries
        self.client = httpx.Client(
            timeout=httpx.Timeout(settings.provider_timeout_seconds),
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, f"{self.base_url}{path}", **kwargs)
            except httpx.TransportError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.25 * (2**attempt))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_error = ProviderError(
                    f"transient provider response {response.status_code}: {response.text[:500]}"
                )
                if attempt < self.max_retries:
                    time.sleep(0.25 * (2**attempt))
                    continue
                break
            try:
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise ProviderError(str(exc)) from exc
            if not isinstance(payload, dict):
                raise ProviderError("provider returned a non-object JSON response")
            return payload
        raise ProviderError(str(last_error)) from last_error

    def healthcheck(self) -> None:
        self.request("GET", "/health")


class QwenEmbeddingClient(_ProviderClient):
    """SiliconFlow Qwen3-VL embedding client using real text and visual inputs."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key.get_secret_value(),
            settings=settings,
        )
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

    def embed_text(self, text: str) -> list[float]:
        return self._embed(text=text)

    def embed_image(self, path: Path, *, text: str | None = None) -> list[float]:
        return self._embed(text=text, media_field="image", media_path=path)

    def embed_video(self, path: Path, *, text: str | None = None) -> list[float]:
        return self._embed(text=text, media_field="video", media_path=path)

    def _embed(
        self,
        *,
        text: str | None = None,
        media_field: str | None = None,
        media_path: Path | None = None,
    ) -> list[float]:
        data = {"model": self.model, "dimensions": str(self.dimension)}
        if text:
            data["text"] = text
        if media_field == "video":
            data["fps"] = str(self.settings.embedding_video_fps)
            data["max_frames"] = str(self.settings.embedding_video_max_frames)
        files: dict[str, tuple[str, Any, str]] = {}
        if media_field and media_path:
            media_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
            with media_path.open("rb") as stream:
                files[media_field] = (media_path.name, stream, media_type)
                payload = self.request("POST", "/v1/embeddings", data=data, files=files)
        else:
            # A (None, value) file tuple forces multipart/form-data for text-only queries too.
            multipart_fields = {key: (None, value) for key, value in data.items()}
            payload = self.request("POST", "/v1/embeddings", files=multipart_fields)
        return self._extract(payload)

    def _extract(self, payload: dict[str, Any]) -> list[float]:
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise ProviderError("embedding provider must return exactly one embedding")
        raw_vector = data[0].get("embedding")
        if not isinstance(raw_vector, list):
            raise ProviderError("embedding provider must return exactly one embedding")
        vector = [float(value) for value in raw_vector]
        if len(vector) != self.dimension:
            raise ProviderError(
                f"embedding dimension mismatch: expected {self.dimension}, got {len(vector)}"
            )
        if not any(value != 0 for value in vector):
            raise ProviderError("embedding provider returned a zero vector")
        return vector


class QwenRerankerClient(_ProviderClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            base_url=settings.reranker_base_url,
            api_key=settings.reranker_api_key.get_secret_value(),
            settings=settings,
        )
        self.model = settings.reranker_model

    def rerank(self, query: dict[str, Any], documents: list[dict[str, Any]]) -> list[float]:
        payload = self.request(
            "POST",
            "/v1/rerank",
            json={
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": len(documents),
                "instruction": "Rank source clips for the user's requested video edit.",
            },
        )
        results = payload.get("results")
        if not isinstance(results, list) or len(results) != len(documents):
            raise ProviderError("reranker returned an invalid result count")
        scores = [0.0] * len(documents)
        seen: set[int] = set()
        for position, item in enumerate(results):
            if not isinstance(item, dict):
                raise ProviderError("reranker returned an invalid result item")
            index = int(item.get("index", position))
            if index < 0 or index >= len(documents) or index in seen:
                raise ProviderError("reranker returned invalid or duplicate indices")
            seen.add(index)
            raw_score = item.get("relevance_score", item.get("score"))
            if not isinstance(raw_score, (int, float)):
                raise ProviderError("reranker result is missing a numeric score")
            scores[index] = float(raw_score)
        return scores


class QwenChatClient(_ProviderClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            settings=settings,
        )
        self.model = settings.llm_model

    def json_completion(self, *, system: str, user: str) -> dict[str, Any]:
        payload = self.request(
            "POST",
            "/v1/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
            result = parse_structured_content(str(content))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("LLM did not return valid structured JSON") from exc
        return result


class SegmentSemantics(BaseModel):
    """Validated visual facts returned by the real multimodal analysis gateway."""

    description: str = Field(min_length=1, max_length=4000)
    scene: str = Field(min_length=1, max_length=512)
    actions: list[str] = Field(default_factory=list, max_length=30)
    people: list[str] = Field(default_factory=list, max_length=30)
    composition: str = Field(min_length=1, max_length=512)
    tags: list[str] = Field(default_factory=list, max_length=50)
    event_type: str | None = Field(default=None, max_length=128)
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_labels: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("actions", "people", "tags", "risk_labels")
    @classmethod
    def clean_strings(cls, values: list[str]) -> list[str]:
        cleaned = [str(value).strip()[:128] for value in values if str(value).strip()]
        return list(dict.fromkeys(cleaned))


class QwenVisualAnalysisClient(_ProviderClient):
    """Direct-video structured visual analysis; never infers semantics from ASR alone."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            settings=settings,
        )
        self.model = settings.llm_model

    def analyze_video(self, path: Path, *, transcript: str = "") -> SegmentSemantics:
        media_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
        prompt = (
            "Analyze only visible/audible facts in this clip. Describe scene, actions, people "
            "without identity inference, composition, retrieval tags, event type and safety risk."
        )
        data = {
            "model": self.model,
            "prompt": prompt,
            "transcript": transcript,
            "response_schema": json.dumps(SegmentSemantics.model_json_schema(), ensure_ascii=False),
        }
        with path.open("rb") as stream:
            payload = self.request(
                "POST",
                "/v1/analyze",
                data=data,
                files={"video": (path.name, stream, media_type)},
            )
        raw = payload.get("analysis", payload)
        try:
            return SegmentSemantics.model_validate(raw)
        except (TypeError, ValueError) as exc:
            raise ProviderError("visual analysis returned invalid structured semantics") from exc


class QwenAsrClient(_ProviderClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            base_url=settings.asr_base_url,
            api_key=settings.asr_api_key.get_secret_value(),
            settings=settings,
        )
        self.model = settings.asr_model

    def transcribe(self, path: Path) -> dict[str, Any]:
        media_type = mimetypes.guess_type(path.name)[0] or "audio/mpeg"
        with path.open("rb") as stream:
            return self.request(
                "POST",
                "/v1/audio/transcriptions",
                data={"model": self.model},
                files={"file": (path.name, stream, media_type)},
            )


def parse_structured_content(content: str) -> dict[str, Any]:
    normalized = content.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()
    try:
        result = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ValueError("model response is not JSON") from exc
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        return {"items": result}
    raise ValueError("model JSON must be an object or array")
