from dataclasses import replace

from backend.app.domain.models import MediaSegment, SearchQuery
from backend.app.retrieval.embeddings import (
    EmbeddingProvider,
    HashEmbeddingProvider,
    cosine_similarity,
    tokenize_text,
)
from backend.app.retrieval.explain import build_reason
from backend.app.retrieval.filters import segment_matches_filters
from backend.app.retrieval.local_index import LocalMediaIndex, LocalSearchResult


class HybridRetriever:
    def __init__(
        self,
        segments: list[MediaSegment],
        *,
        embedding_provider: EmbeddingProvider | None = None,
        lexical_weight: float = 0.6,
        dense_weight: float = 0.4,
    ) -> None:
        self._segments = segments
        self._embedding_provider = embedding_provider or HashEmbeddingProvider()
        self._lexical_weight = lexical_weight
        self._dense_weight = dense_weight

    def search(self, query: SearchQuery) -> list[LocalSearchResult]:
        top_k = max(query.top_k, 1)
        candidate_query = query.model_copy(update={"top_k": len(self._segments) or top_k})
        lexical_results = LocalMediaIndex(self._segments).search(candidate_query)
        dense_results = [
            result
            for result in self.dense_search(candidate_query)
            if result.score > 0
        ]

        lexical_scores = {result.segment_id: result.score for result in lexical_results}
        dense_scores = {result.segment_id: result.score for result in dense_results}
        lexical_by_id = {result.segment_id: result for result in lexical_results}
        dense_by_id = {result.segment_id: result for result in dense_results}

        fused_results: list[LocalSearchResult] = []
        for segment_id in sorted(set(lexical_by_id) | set(dense_by_id)):
            base = lexical_by_id.get(segment_id) or dense_by_id[segment_id]
            fused_score = (
                self._lexical_weight * _normalize_score(lexical_scores.get(segment_id, 0.0), lexical_scores)
                + self._dense_weight * _normalize_score(dense_scores.get(segment_id, 0.0), dense_scores)
            )
            fused_results.append(
                replace(
                    base,
                    score=fused_score,
                    lexical_score=lexical_scores.get(segment_id),
                    dense_score=dense_scores.get(segment_id),
                    matched_tags=tuple(
                        sorted(
                            set(lexical_by_id.get(segment_id, base).matched_tags)
                            | set(dense_by_id.get(segment_id, base).matched_tags)
                        )
                    ),
                )
            )

        return sorted(
            fused_results,
            key=lambda result: (result.score, result.highlight_score, result.motion_score, result.segment_id),
            reverse=True,
        )[:top_k]

    def dense_search(self, query: SearchQuery) -> list[LocalSearchResult]:
        query_embedding = self._embedding_provider.embed_text(query.query_text)
        query_terms = set(tokenize_text(query.query_text))
        results: list[LocalSearchResult] = []

        for segment in self._filtered_segments(query):
            dense_score = cosine_similarity(
                query_embedding,
                self._embedding_provider.embed_text(_segment_text(segment)),
            )
            overlap_score = _token_overlap_score(query_terms, set(tokenize_text(_segment_text(segment))))
            score = dense_score + overlap_score
            reason, evidence = build_reason(segment, _matched_fields(segment, query_terms))
            results.append(
                LocalSearchResult(
                    segment_id=segment.segment_id,
                    video_id=segment.video_id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    score=score,
                    reason=reason,
                    evidence=evidence,
                    creative_suggestion=None,
                    motion_score=segment.motion_score,
                    highlight_score=segment.highlight_score,
                    dense_score=score,
                    matched_tags=_matched_tags(segment, query_terms),
                )
            )

        return sorted(
            results,
            key=lambda result: (result.score, result.highlight_score, result.motion_score, result.segment_id),
            reverse=True,
        )[: query.top_k]

    def _filtered_segments(self, query: SearchQuery) -> list[MediaSegment]:
        return [
            segment
            for segment in self._segments
            if segment_matches_filters(segment, query.filters)
        ]


def _normalize_score(score: float, scores: dict[str, float]) -> float:
    if score <= 0 or not scores:
        return 0.0
    max_score = max(scores.values())
    if max_score <= 0:
        return 0.0
    return score / max_score


def _segment_text(segment: MediaSegment) -> str:
    return " ".join(
        [
            segment.asr_transcript,
            segment.ocr_text,
            " ".join(segment.frame_captions),
            " ".join(segment.tags),
        ]
    )


def _token_overlap_score(query_terms: set[str], segment_terms: set[str]) -> float:
    if not query_terms:
        return 0.0
    return len(query_terms & segment_terms) / len(query_terms)


def _matched_fields(segment: MediaSegment, query_terms: set[str]) -> set[str]:
    matched_fields: set[str] = set()
    field_values = {
        "asr_transcript": segment.asr_transcript,
        "ocr_text": segment.ocr_text,
        "frame_captions": " ".join(segment.frame_captions),
        "tags": " ".join(segment.tags),
    }
    for field_name, value in field_values.items():
        field_terms = set(tokenize_text(value))
        if query_terms & field_terms:
            matched_fields.add(field_name)
    return matched_fields


def _matched_tags(segment: MediaSegment, query_terms: set[str]) -> tuple[str, ...]:
    return tuple(sorted(tag for tag in segment.tags if tag.lower() in query_terms))
