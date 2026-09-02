from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Candidate:
    segment_id: str
    score: float
    duration: float
    risk_score: float = 0.0
    freshness_score: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FusionConfig:
    rrf_k: int = 60
    semantic_weight: float = 0.6
    risk_weight: float = 0.2
    freshness_weight: float = 0.1
    compactness_weight: float = 0.1


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    segment_id: str
    fusion_score: float
    route_scores: dict[str, float]
    route_ranks: dict[str, int]
    metadata: dict[str, object]


@dataclass(slots=True)
class _Accumulator:
    rrf: float
    route_scores: dict[str, float]
    route_ranks: dict[str, int]
    candidate: Candidate


def fuse_candidates(
    routes: dict[str, list[Candidate]], config: FusionConfig | None = None
) -> list[FusedCandidate]:
    config = config or FusionConfig()
    if config.rrf_k <= 0:
        raise ValueError("rrf_k must be positive")

    aggregated: dict[str, _Accumulator] = {}
    for route_name, candidates in routes.items():
        for rank, candidate in enumerate(candidates, start=1):
            item = aggregated.setdefault(
                candidate.segment_id,
                _Accumulator(rrf=0.0, route_scores={}, route_ranks={}, candidate=candidate),
            )
            item.rrf += 1.0 / (config.rrf_k + rank)
            item.route_scores[route_name] = candidate.score
            item.route_ranks[route_name] = rank
            if candidate.score > item.candidate.score:
                item.candidate = candidate

    max_rrf = max((item.rrf for item in aggregated.values()), default=1.0)
    result: list[FusedCandidate] = []
    for segment_id, item in aggregated.items():
        candidate = item.candidate
        compactness = 1.0 / (1.0 + max(candidate.duration, 0.0))
        semantic = item.rrf / max_rrf
        score = (
            config.semantic_weight * semantic
            + config.risk_weight * _bounded(candidate.risk_score)
            + config.freshness_weight * _bounded(candidate.freshness_score)
            + config.compactness_weight * compactness
        )
        result.append(
            FusedCandidate(
                segment_id=segment_id,
                fusion_score=score,
                route_scores=dict(item.route_scores),
                route_ranks=dict(item.route_ranks),
                metadata=dict(candidate.metadata),
            )
        )
    return sorted(result, key=lambda item: (-item.fusion_score, item.segment_id))


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))
