from dataclasses import dataclass

from backend.app.domain.models import CreativeSuggestion, MediaSegment, SearchQuery, SegmentEvidence
from backend.app.retrieval.explain import build_reason
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
        results: list[LocalSearchResult] = []

        for segment in self._segments:
            score, matched_fields = _lexical_score(segment, terms)
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
                )
            )

        return sorted(results, key=lambda result: result.score, reverse=True)[: query.top_k]


def _lexical_score(segment: MediaSegment, terms: list[str]) -> tuple[float, set[str]]:
    score = 0.0
    matched_fields: set[str] = set()
    field_values = {
        "asr_transcript": segment.asr_transcript,
        "ocr_text": segment.ocr_text,
        "frame_captions": " ".join(segment.frame_captions),
        "tags": " ".join(segment.tags),
    }
    field_weights = {
        "asr_transcript": 1.0,
        "ocr_text": 1.0,
        "frame_captions": 0.9,
        "tags": 1.2,
    }

    for field_name, raw_value in field_values.items():
        value = raw_value.lower()
        for term in terms:
            normalized_term = term.lower()
            if normalized_term and normalized_term in value:
                score += field_weights[field_name]
                matched_fields.add(field_name)

    return score, matched_fields
