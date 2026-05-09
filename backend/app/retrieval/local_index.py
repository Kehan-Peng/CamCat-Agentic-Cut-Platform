from dataclasses import dataclass
import math

from backend.app.domain.models import CreativeSuggestion, MediaSegment, SearchQuery, SegmentEvidence
from backend.app.retrieval.explain import build_reason
from backend.app.retrieval.embeddings import tokenize_text
from backend.app.retrieval.filters import segment_matches_filters
from backend.app.retrieval.query_rewrite import rewrite_query


@dataclass(frozen=True)
class LocalSearchResult:
    segment_id: str
    video_id: str
    start_time: float
    end_time: float
    score: float
    reason: str
    evidence: list[SegmentEvidence]
    creative_suggestion: CreativeSuggestion | None
    motion_score: float
    highlight_score: float
    lexical_score: float | None = None
    dense_score: float | None = None
    matched_tags: tuple[str, ...] = ()

    def to_response(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "video_id": self.video_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "score": round(self.score, 4),
            "reason": self.reason,
            "evidence": [item.model_dump() for item in self.evidence],
            "creative_suggestion": (
                self.creative_suggestion.model_dump()
                if self.creative_suggestion is not None
                else None
            ),
        }


class LocalMediaIndex:
    def __init__(self, segments: list[MediaSegment]) -> None:
        self._segments = segments

    def search(self, query: SearchQuery) -> list[LocalSearchResult]:
        rewritten = rewrite_query(query.query_text)
        terms = rewritten.expanded_queries
        searchable_segments = [
            segment
            for segment in self._segments
            if segment_matches_filters(segment, query.filters)
        ]
        corpus_stats = _build_corpus_stats(searchable_segments, terms)
        results: list[LocalSearchResult] = []

        for segment in searchable_segments:
            score, matched_fields = _lexical_score(segment, terms, corpus_stats)
            if score <= 0:
                continue

            reason, evidence = build_reason(segment, matched_fields)
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
                    lexical_score=score,
                    matched_tags=_matched_tags(segment, terms),
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[: query.top_k]


@dataclass(frozen=True)
class _CorpusStats:
    document_count: int
    document_frequency: dict[str, int]
    average_field_length: dict[str, float]


def _lexical_score(
    segment: MediaSegment,
    terms: list[str],
    corpus_stats: _CorpusStats | None = None,
) -> tuple[float, set[str]]:
    if corpus_stats is None:
        corpus_stats = _build_corpus_stats([segment], terms)

    score = 0.0
    matched_fields: set[str] = set()
    field_weights = {
        "asr_transcript": 1.0,
        "ocr_text": 1.0,
        "frame_captions": 0.9,
        "tags": 1.2,
    }

    for field_name, raw_value in _field_values(segment).items():
        value = raw_value.lower()
        field_length = max(len(tokenize_text(value)), 1)
        average_field_length = max(corpus_stats.average_field_length.get(field_name, 1.0), 1.0)
        for term in terms:
            normalized_term = term.lower()
            term_frequency = _term_frequency(value, normalized_term)
            if term_frequency > 0:
                score += (
                    field_weights[field_name]
                    * _idf(normalized_term, corpus_stats)
                    * _bm25_term_weight(term_frequency, field_length, average_field_length)
                )
                matched_fields.add(field_name)

    return score, matched_fields


def _build_corpus_stats(segments: list[MediaSegment], terms: list[str]) -> _CorpusStats:
    document_frequency = {term.lower(): 0 for term in terms if term}
    field_lengths: dict[str, list[int]] = {
        "asr_transcript": [],
        "ocr_text": [],
        "frame_captions": [],
        "tags": [],
    }

    for segment in segments:
        seen_terms: set[str] = set()
        for field_name, value in _field_values(segment).items():
            normalized_value = value.lower()
            field_lengths[field_name].append(max(len(tokenize_text(normalized_value)), 1))
            for term in document_frequency:
                if term and _term_frequency(normalized_value, term) > 0:
                    seen_terms.add(term)

        for term in seen_terms:
            document_frequency[term] += 1

    average_field_length = {
        field_name: (sum(lengths) / len(lengths)) if lengths else 1.0
        for field_name, lengths in field_lengths.items()
    }
    return _CorpusStats(
        document_count=len(segments),
        document_frequency=document_frequency,
        average_field_length=average_field_length,
    )


def _field_values(segment: MediaSegment) -> dict[str, str]:
    return {
        "asr_transcript": segment.asr_transcript,
        "ocr_text": segment.ocr_text,
        "frame_captions": " ".join(segment.frame_captions),
        "tags": " ".join(segment.tags),
    }


def _matched_tags(segment: MediaSegment, terms: list[str]) -> tuple[str, ...]:
    query_terms = {term.lower() for term in terms if term}
    return tuple(sorted(tag for tag in segment.tags if tag.lower() in query_terms))


def _term_frequency(value: str, term: str) -> int:
    if not term:
        return 0
    tokens = tokenize_text(value)
    exact_matches = sum(1 for token in tokens if token == term)
    if exact_matches:
        return exact_matches
    return value.count(term)


def _idf(term: str, corpus_stats: _CorpusStats) -> float:
    document_count = max(corpus_stats.document_count, 1)
    frequency = corpus_stats.document_frequency.get(term, 0)
    return math.log(1.0 + ((document_count - frequency + 0.5) / (frequency + 0.5)))


def _bm25_term_weight(
    term_frequency: int,
    field_length: int,
    average_field_length: float,
) -> float:
    k1 = 1.2
    b = 0.25
    denominator = term_frequency + k1 * (1.0 - b + b * (field_length / average_field_length))
    return (term_frequency * (k1 + 1.0)) / denominator
