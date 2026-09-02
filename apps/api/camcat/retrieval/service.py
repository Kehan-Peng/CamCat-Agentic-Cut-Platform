from __future__ import annotations

import base64
import binascii
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from camcat.retrieval.fusion import Candidate, FusionConfig, fuse_candidates
from camcat.retrieval.milvus_store import MilvusSegmentStore, build_filter_expression
from camcat.services.providers import QwenEmbeddingClient, QwenRerankerClient


@dataclass(frozen=True, slots=True)
class RankedMaterial:
    segment_id: str
    score: float
    reranker_score: float
    entity: dict[str, Any]
    route_scores: dict[str, float]
    route_ranks: dict[str, int]


class RetrievalService:
    def __init__(
        self,
        *,
        store: MilvusSegmentStore,
        embedding: QwenEmbeddingClient,
        reranker: QwenRerankerClient,
        fusion_config: FusionConfig | None = None,
    ) -> None:
        self.store = store
        self.embedding = embedding
        self.reranker = reranker
        self.fusion_config = fusion_config or FusionConfig()

    def search(
        self,
        *,
        query_text: str | None,
        query_image_base64: str | None,
        filters: dict[str, Any],
        top_k: int,
    ) -> list[RankedMaterial]:
        image_path: Path | None = None
        try:
            if query_image_base64:
                image_path = _write_query_image(query_image_base64)
                vector = self.embedding.embed_image(image_path, text=query_text)
            elif query_text:
                vector = self.embedding.embed_text(query_text)
            else:
                raise ValueError("text or image query is required")

            candidate_limit = min(200, max(50, top_k * 5))
            expression = build_filter_expression(
                {key: value for key, value in filters.items() if key == "asset_id"}
            )
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="camcat-recall") as pool:
                dense_future = pool.submit(
                    self.store.dense_search,
                    vector,
                    limit=candidate_limit,
                    filter_expression=expression,
                )
                bm25_future = pool.submit(
                    self.store.bm25_search,
                    query_text or "",
                    limit=candidate_limit,
                    filter_expression=expression,
                )
                scalar_future = pool.submit(
                    self.store.scalar_search, filters, limit=candidate_limit
                )
                raw_routes = {
                    "dense": dense_future.result(),
                    "bm25": bm25_future.result(),
                    "scalar": scalar_future.result(),
                }

            entity_by_id: dict[str, dict[str, Any]] = {}
            routes: dict[str, list[Candidate]] = {}
            now = int(time.time())
            for route_name, hits in raw_routes.items():
                routes[route_name] = []
                for hit in hits:
                    entity_by_id[hit.segment_id] = hit.entity
                    age_days = max(
                        0.0, (now - int(hit.entity.get("created_at_epoch", now))) / 86400
                    )
                    routes[route_name].append(
                        Candidate(
                            segment_id=hit.segment_id,
                            score=hit.score,
                            duration=float(hit.entity.get("duration", 0.0)),
                            risk_score=float(hit.entity.get("risk_score", 0.0)),
                            freshness_score=max(0.0, 1.0 - age_days / 30.0),
                            metadata=hit.entity,
                        )
                    )

            fused = fuse_candidates(routes, self.fusion_config)[:candidate_limit]
            if not fused:
                return []
            query: dict[str, Any] = {"text": query_text or ""}
            if query_image_base64:
                query["image_base64"] = query_image_base64
            documents = [
                {
                    "text": str(entity_by_id[item.segment_id].get("description_text", "")),
                    "metadata": {
                        "tags": entity_by_id[item.segment_id].get("tags", []),
                        "event_type": entity_by_id[item.segment_id].get("event_type", ""),
                        "risk_score": entity_by_id[item.segment_id].get("risk_score", 0.0),
                        "semantic_metadata": entity_by_id[item.segment_id].get(
                            "semantic_metadata", {}
                        ),
                        "license_name": entity_by_id[item.segment_id].get("license_name", ""),
                        "source_url": entity_by_id[item.segment_id].get("source_url", ""),
                    },
                }
                for item in fused
            ]
            reranker_scores = self.reranker.rerank(query, documents)
            ranked = [
                RankedMaterial(
                    segment_id=item.segment_id,
                    score=item.fusion_score,
                    reranker_score=reranker_scores[index],
                    entity=entity_by_id[item.segment_id],
                    route_scores=item.route_scores,
                    route_ranks=item.route_ranks,
                )
                for index, item in enumerate(fused)
            ]
            return sorted(
                ranked,
                key=lambda item: (
                    -(0.75 * item.reranker_score + 0.25 * item.score),
                    item.segment_id,
                ),
            )[:top_k]
        finally:
            if image_path is not None:
                image_path.unlink(missing_ok=True)


def _write_query_image(value: str) -> Path:
    encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("query_image_base64 is not valid base64") from exc
    if not content or len(content) > 20 * 1024 * 1024:
        raise ValueError("query image must be between 1 byte and 20 MiB")
    descriptor, raw_path = tempfile.mkstemp(prefix="camcat-query-", suffix=".jpg")
    import os

    os.close(descriptor)
    path = Path(raw_path)
    path.write_bytes(content)
    return path
