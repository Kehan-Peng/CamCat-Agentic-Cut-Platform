import math

from backend.app.retrieval.evaluation import (
    mean_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
)


def test_recall_at_k_counts_relevant_ids_in_prefix():
    ranked_ids = ["s1", "s2", "s3", "s4"]

    assert recall_at_k(ranked_ids, {"s2", "s4"}, 3) == 0.5


def test_mean_reciprocal_rank_uses_first_relevant_position():
    ranked_ids = ["s1", "s2", "s3"]

    assert mean_reciprocal_rank(ranked_ids, {"s3", "s2"}) == 0.5
    assert mean_reciprocal_rank(ranked_ids, {"missing"}) == 0.0


def test_ndcg_at_k_uses_graded_relevance_and_ideal_ranking():
    ranked_ids = ["s1", "s2", "s3"]
    relevance_by_id = {"s1": 1.0, "s2": 3.0, "s3": 2.0}

    actual = (2**1 - 1) / math.log2(2) + (2**3 - 1) / math.log2(3)
    ideal = (2**3 - 1) / math.log2(2) + (2**2 - 1) / math.log2(3)

    assert ndcg_at_k(ranked_ids, relevance_by_id, 2) == actual / ideal
    assert ndcg_at_k(ranked_ids, {}, 2) == 0.0
