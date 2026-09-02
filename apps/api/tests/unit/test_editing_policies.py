from __future__ import annotations

from datetime import UTC, datetime, timedelta

from camcat.editing.policies import (
    choose_aspect_ratio,
    enforce_timeline_policy,
    expiry_for_upload,
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


def test_timeline_always_keeps_user_source_primary_and_caps_library_at_25_percent() -> None:
    proposed = [
        {"segment_id": "lib:1", "origin": "library", "source_start": 0, "source_end": 4},
        {"segment_id": "source:a:1", "origin": "source", "source_start": 0, "source_end": 6},
        {"segment_id": "lib:2", "origin": "library", "source_start": 0, "source_end": 4},
        {"segment_id": "source:a:2", "origin": "source", "source_start": 2, "source_end": 8},
    ]

    result = enforce_timeline_policy(proposed, external_ratio_limit=0.25)

    source_duration = sum(
        item["output_end"] - item["output_start"] for item in result if item["origin"] == "source"
    )
    library_duration = sum(
        item["output_end"] - item["output_start"] for item in result if item["origin"] == "library"
    )
    assert source_duration > library_duration
    assert library_duration / (source_duration + library_duration) <= 0.25 + 1e-9
    assert result[0]["origin"] == "source"


def test_explicit_request_can_raise_external_material_limit() -> None:
    proposed = [
        {"segment_id": "source:a:1", "origin": "source", "source_start": 0, "source_end": 6},
        {"segment_id": "lib:1", "origin": "library", "source_start": 0, "source_end": 4},
    ]

    result = enforce_timeline_policy(proposed, external_ratio_limit=0.5)

    assert result[-1]["source_end"] - result[-1]["source_start"] == 4
