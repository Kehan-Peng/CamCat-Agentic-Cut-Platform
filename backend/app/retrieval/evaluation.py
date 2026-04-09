import math
from collections.abc import Iterable, Mapping


def recall_at_k(ranked_ids: Iterable[str], relevant_ids: Iterable[str], k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant or k <= 0:
        return 0.0
    retrieved = set(list(ranked_ids)[:k])
    return len(retrieved & relevant) / len(relevant)


def mean_reciprocal_rank(ranked_ids: Iterable[str], relevant_ids: Iterable[str]) -> float:
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0

    for index, item_id in enumerate(ranked_ids, start=1):
        if item_id in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: Iterable[str], relevance_by_id: Mapping[str, float], k: int) -> float:
    if k <= 0 or not relevance_by_id:
        return 0.0

    ranked_relevances = [relevance_by_id.get(item_id, 0.0) for item_id in list(ranked_ids)[:k]]
    ideal_relevances = sorted(
        (score for score in relevance_by_id.values() if score > 0),
        reverse=True,
    )[:k]
    ideal = _discounted_cumulative_gain(ideal_relevances)
    if ideal <= 0:
        return 0.0
    return _discounted_cumulative_gain(ranked_relevances) / ideal


def _discounted_cumulative_gain(relevances: Iterable[float]) -> float:
    return sum(
        ((2**relevance) - 1.0) / math.log2(index + 1)
        for index, relevance in enumerate(relevances, start=1)
        if relevance > 0
    )
