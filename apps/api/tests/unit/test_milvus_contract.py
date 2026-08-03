from __future__ import annotations

from unittest.mock import Mock

import pytest
from camcat.config import Settings
from camcat.retrieval.milvus_store import MilvusSegmentStore


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        embedding_base_url="https://provider.example",
        embedding_api_key="test-key",
        reranker_base_url="https://provider.example",
        reranker_api_key="test-key",
        llm_base_url="https://provider.example",
        llm_api_key="test-key",
        asr_base_url="https://provider.example",
        asr_api_key="test-key",
    )


def test_semantic_metadata_schema_uses_a_new_collection_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAMCAT_MILVUS_COLLECTION", raising=False)
    assert _settings().milvus_collection == "camcat_segments_v7"


def test_upsert_rejects_rows_without_license_source_and_semantics() -> None:
    store = MilvusSegmentStore(_settings())
    store._client = Mock()

    with pytest.raises(ValueError, match="semantic_metadata, license_name and source_url"):
        store.upsert(
            {
                "multimodal_embedding": [0.0] * 2048,
                "embedding_model": "Qwen/Qwen3-VL-Embedding-8B",
            }
        )
    store._client.upsert.assert_not_called()

    with pytest.raises(ValueError, match="storage_key"):
        store.upsert(
            {
                "multimodal_embedding": [0.1] * 2048,
                "embedding_model": "Qwen/Qwen3-VL-Embedding-8B",
                "semantic_metadata": {"scene": "shore"},
                "license_name": "Pixabay",
                "source_url": "https://pixabay.example/source",
            }
        )


def test_existing_collection_waits_for_concurrent_index_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = MilvusSegmentStore(_settings())
    client = Mock()
    client.has_collection.return_value = True
    client.describe_collection.return_value = {
        "fields": [
            {"name": name, "params": {"dim": 2048}}
            for name in (
                *store.output_fields,
                "multimodal_embedding",
                "sparse",
            )
        ]
    }
    client.list_indexes.side_effect = [
        ["multimodal_embedding"],
        ["multimodal_embedding", "sparse"],
    ]
    store._client = client
    monkeypatch.setattr("camcat.retrieval.milvus_store.time.sleep", lambda _seconds: None)

    store.ensure_collection()

    assert client.list_indexes.call_count == 2
    client.load_collection.assert_called_once_with(collection_name=store.collection)
