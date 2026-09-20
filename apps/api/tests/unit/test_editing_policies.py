from __future__ import annotations

from datetime import UTC, datetime, timedelta

from camcat.editing.policies import (
    choose_aspect_ratio,
    expiry_for_upload,
    explicit_external_ratio,
    prepare_source_candidates,
    resolution_for_ratio,
)


def test_uploads_expire_exactly_four_hours_after_creation() -> None:
    created = datetime(2026, 7, 19, 8, 30, tzinfo=UTC)

    assert expiry_for_upload(created) == created + timedelta(hours=4)


def test_aspect_ratio_uses_explicit_intent_then_source_shape() -> None:
    assert choose_aspect_ratio("做成小红书竖屏 3:4", 1920, 1080) == "3:4"
    assert choose_aspect_ratio("发 TikTok", 1920, 1080) == "9:16"
    assert choose_aspect_ratio("保留原画幅", 1080, 1080) == "1:1"
    assert choose_aspect_ratio("旅行 vlog", 1920, 1080) == "16:9"
    assert choose_aspect_ratio("旅行 vlog", 1440, 1080) == "4:3"
    assert resolution_for_ratio("3:4") == (1080, 1440)


def test_duplicate_source_shots_are_removed_but_order_is_stable() -> None:
    candidates = [
        {"segment_id": "source:a:1", "shot_signature": "same", "quality_score": 0.92},
        {"segment_id": "source:a:2", "shot_signature": "same", "quality_score": 0.42},
        {"segment_id": "source:b:1", "shot_signature": "unique", "quality_score": 0.78},
    ]

    prepared = prepare_source_candidates(candidates)

    assert [item["segment_id"] for item in prepared] == ["source:a:1", "source:b:1"]


def test_external_material_limit_is_explicit_and_bounded() -> None:
    assert explicit_external_ratio("素材库最多 40%") == 0.4
    assert explicit_external_ratio("普通剪辑") == 0.25
    assert explicit_external_ratio("stock 99%") == 0.75
