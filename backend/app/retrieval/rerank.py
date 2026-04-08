from dataclasses import replace

from backend.app.retrieval.local_index import LocalSearchResult


def rerank_results(results: list[LocalSearchResult]) -> list[LocalSearchResult]:
    reranked = [
        replace(
            result,
            score=result.score + (0.25 * result.motion_score) + (0.35 * result.highlight_score),
        )
        for result in results
    ]
    return sorted(
        reranked,
        key=lambda result: (result.score, result.motion_score, result.highlight_score),
        reverse=True,
    )
