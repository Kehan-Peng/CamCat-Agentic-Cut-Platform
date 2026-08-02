from camcat.retrieval.fusion import Candidate, FusionConfig, fuse_candidates


def test_rrf_unions_routes_deduplicates_and_keeps_provenance() -> None:
    routes = {
        "dense": [
            Candidate("seg-a", 0.92, duration=4.0, risk_score=0.4),
            Candidate("seg-b", 0.88, duration=8.0, risk_score=0.9),
        ],
        "bm25": [
            Candidate("seg-b", 12.5, duration=8.0, risk_score=0.9),
            Candidate("seg-c", 9.2, duration=3.0, risk_score=0.2),
        ],
        "scalar": [Candidate("seg-b", 1.0, duration=8.0, risk_score=0.9)],
    }

    ranked = fuse_candidates(routes, FusionConfig(rrf_k=60, semantic_weight=0.6))

    assert [item.segment_id for item in ranked].count("seg-b") == 1
    assert ranked[0].segment_id == "seg-b"
    assert set(ranked[0].route_scores) == {"dense", "bm25", "scalar"}
    assert ranked[0].fusion_score > ranked[-1].fusion_score


def test_compact_clips_win_when_retrieval_signals_are_equal() -> None:
    routes = {
        "dense": [
            Candidate("long", 0.9, duration=20.0, risk_score=0.0),
            Candidate("short", 0.9, duration=4.0, risk_score=0.0),
        ]
    }

    ranked = fuse_candidates(
        routes,
        FusionConfig(compactness_weight=0.4, semantic_weight=0.6, risk_weight=0.0),
    )

    assert ranked[0].segment_id == "short"
