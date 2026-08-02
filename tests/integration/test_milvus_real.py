from __future__ import annotations

from time import time
from uuid import uuid4

import pytest
from camcat.config import get_settings
from camcat.retrieval.milvus_store import MilvusSegmentStore

pytestmark = pytest.mark.integration


def test_real_milvus_dense_bm25_and_scalar_routes() -> None:
    settings = get_settings().model_copy(
        update={"milvus_collection": f"camcat_integration_{uuid4().hex[:12]}"}
    )
    store = MilvusSegmentStore(settings)
    store.ensure_collection()
    vector = [0.0] * settings.embedding_dimension
    vector[7] = 1.0
    segment_id = str(uuid4())
    try:
        store.upsert(
            {
                "segment_id": segment_id,
                "asset_id": str(uuid4()),
                "multimodal_embedding": vector,
                "description_text": "雨夜城市街道上的快速运动镜头",
                "start_time": 0.0,
                "end_time": 4.0,
                "duration": 4.0,
                "risk_score": 0.7,
                "created_at_epoch": int(time()),
                "trigger_type": "scene_cut",
                "event_type": "fast_motion",
                "tags": ["雨夜", "城市"],
                "embedding_model": settings.embedding_model,
                "embedding_dimension": settings.embedding_dimension,
            }
        )
        assert store.dense_search(vector, limit=5)[0].segment_id == segment_id
        assert store.bm25_search("雨夜 城市", limit=5)[0].segment_id == segment_id
        assert (
            store.scalar_search({"event_type": "fast_motion"}, limit=5)[0].segment_id == segment_id
        )
    finally:
        store.client.drop_collection(collection_name=store.collection)
