from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

SUPPORTED_RATIOS = ("16:9", "9:16", "3:4", "4:3", "1:1")
RATIO_RESOLUTIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "3:4": (1080, 1440),
    "4:3": (1440, 1080),
    "1:1": (1080, 1080),
}


def expiry_for_upload(created_at: datetime) -> datetime:
    return created_at + timedelta(hours=4)


def choose_aspect_ratio(instruction: str, width: int, height: int) -> str:
    normalized = instruction.lower().replace("：", ":")
    for ratio in SUPPORTED_RATIOS:
        if ratio in normalized:
            return ratio
    if re.search(r"tiktok|抖音|reels?|shorts?|竖屏|手机全屏", normalized):
        return "9:16"
    if re.search(r"小红书|rednote", normalized):
        return "3:4"
    if re.search(r"方形|square", normalized):
        return "1:1"
    if width <= 0 or height <= 0:
        return "16:9"
    source = width / height
    return min(
        SUPPORTED_RATIOS,
        key=lambda value: abs(source - _ratio_value(value)),
    )


def resolution_for_ratio(ratio: str) -> tuple[int, int]:
    try:
        return RATIO_RESOLUTIONS[ratio]
    except KeyError as exc:
        raise ValueError(f"unsupported aspect ratio: {ratio}") from exc


def prepare_source_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the strongest representative of repeated shots without reshuffling the story."""
    items = [dict(item) for item in candidates]
    best_for_signature: dict[str, int] = {}
    for index, item in enumerate(items):
        signature = str(item.get("shot_signature") or item.get("segment_id") or index)
        incumbent_index = best_for_signature.get(signature)
        if incumbent_index is None or float(item.get("quality_score", 0)) > float(
            items[incumbent_index].get("quality_score", 0)
        ):
            best_for_signature[signature] = index
    selected = set(best_for_signature.values())
    return [item for index, item in enumerate(items) if index in selected]


def explicit_external_ratio(instruction: str) -> float:
    normalized = instruction.lower()
    match = re.search(r"(?:外部|素材库|stock)[^%\d]{0,12}(\d{1,2})\s*%", normalized)
    if match:
        return min(0.75, max(0.0, int(match.group(1)) / 100))
    if re.search(r"全部使用外部|主要使用素材库|stock[- ]?only", normalized):
        return 0.75
    return 0.25


def _ratio_value(ratio: str) -> float:
    left, right = ratio.split(":", 1)
    return int(left) / int(right)
