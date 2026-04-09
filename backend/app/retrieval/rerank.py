from dataclasses import replace

from backend.app.retrieval.embeddings import tokenize_text
from backend.app.retrieval.local_index import LocalSearchResult


def rerank_results(
    results: list[LocalSearchResult],
    *,
    query_text: str | None = None,
) -> list[LocalSearchResult]:
    score_maps = {
        "base": {result.segment_id: result.score for result in results},
        "lexical": {
            result.segment_id: result.lexical_score or 0.0
            for result in results
        },
        "dense": {
            result.segment_id: result.dense_score or 0.0
            for result in results
        },
    }
    query_terms = set(tokenize_text(query_text or ""))

    reranked = [replace(result, score=_rerank_score(result, score_maps, query_terms)) for result in results]
    return sorted(
        reranked,
        key=lambda result: (-result.score, -result.motion_score, -result.highlight_score, result.segment_id),
    )


def _rerank_score(
    result: LocalSearchResult,
    score_maps: dict[str, dict[str, float]],
    query_terms: set[str],
) -> float:
    base_score = _normalize_score(result.score, score_maps["base"])
    lexical_score = _normalize_score(result.lexical_score or result.score, score_maps["lexical"])
    dense_score = _normalize_score(result.dense_score or 0.0, score_maps["dense"])
    tag_score = _tag_match_score(result.matched_tags, query_terms)

    return (
        (0.40 * base_score)
        + (0.20 * lexical_score)
        + (0.20 * dense_score)
        + (0.15 * result.motion_score)
        + (0.20 * result.highlight_score)
        + (0.25 * tag_score)
    )


def _normalize_score(score: float, scores: dict[str, float]) -> float:
    if score <= 0:
        return 0.0
    max_score = max(scores.values(), default=0.0)
    if max_score <= 0:
        return 0.0
    return score / max_score


def _tag_match_score(matched_tags: tuple[str, ...], query_terms: set[str]) -> float:
    if not matched_tags:
        return 0.0
    if not query_terms:
        return 1.0
    matched = {tag.lower() for tag in matched_tags}
    return len(matched & query_terms) / len(query_terms)
