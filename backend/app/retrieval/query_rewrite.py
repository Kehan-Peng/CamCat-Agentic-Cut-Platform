from pydantic import BaseModel, Field


class QueryRewrite(BaseModel):
    original_query: str
    normalized_query: str
    expanded_queries: list[str] = Field(default_factory=list)


def rewrite_query(query_text: str) -> QueryRewrite:
    normalized = " ".join(query_text.strip().lower().split())
    expanded = _unique([normalized, *_split_terms(normalized)])

    if _is_hot_blooded_cut_query(normalized):
        expanded = _unique(
            [
                *expanded,
                "热血",
                "卡点",
                "高能",
                "团战",
                "胜利",
                "快节奏",
                "冲刺",
                "反打",
                "沸腾",
                "high_energy",
                "hot_blooded",
                "highlight",
            ]
        )

    return QueryRewrite(
        original_query=query_text,
        normalized_query=normalized,
        expanded_queries=[term for term in expanded if term],
    )


def _is_hot_blooded_cut_query(normalized: str) -> bool:
    return ("热血" in normalized and "卡点" in normalized) or "hot_blooded" in normalized


def _split_terms(normalized: str) -> list[str]:
    terms = normalized.replace("/", " ").replace(",", " ").split()
    return [term for term in terms if term]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values
