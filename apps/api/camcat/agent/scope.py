from __future__ import annotations


def editing_retrieval_filters(*, base_asset_id: str | None) -> dict[str, str]:
    """Allow edit-time recall to add supplementary footage from the whole library."""

    _ = base_asset_id
    return {}


def needs_material_retrieval(instruction: str) -> bool:
    """Cheap routing guard for edits that cannot change the material timeline."""

    normalized = instruction.lower()
    for phrase in ("不改镜头", "不调整镜头", "keep clips", "keep timeline"):
        normalized = normalized.replace(phrase, "")
    lightweight_terms = ("标题", "title", "字幕", "subtitle", "caption", "文案")
    timeline_terms = (
        "剪",
        "镜头",
        "素材",
        "节奏",
        "时长",
        "重排",
        "b-roll",
        "clip",
        "timeline",
        "transition",
        "转场",
    )
    return not (
        any(term in normalized for term in lightweight_terms)
        and not any(term in normalized for term in timeline_terms)
    )
