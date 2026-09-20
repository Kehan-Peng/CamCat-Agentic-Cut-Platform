from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from camcat.editing.speech import (
    SpeechDecision,
    SpeechDecisionKind,
    SpeechEditingPlan,
)

_SPEECH_TERMS = (
    "口播",
    "采访",
    "访谈",
    "教程",
    "讲解",
    "vlog",
    "talking-head",
    "interview",
    "tutorial",
    "speech",
)


def is_speech_heavy(instruction: str, intent: dict[str, Any]) -> bool:
    haystack = " ".join(
        [instruction, str(intent.get("style", "")), str(intent.get("story_arc", ""))]
    ).lower()
    return any(term in haystack for term in _SPEECH_TERMS)


def collect_speech_evidence(clips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for clip in clips:
        clip_id = str(clip["clip_id"])
        source_id = str(clip.get("media_id") or clip.get("segment_id"))
        segment_start = float(clip.get("segment_start", clip["source_start"]))
        clip_start = round(float(clip["source_start"]) * 1_000_000)
        clip_end = round(float(clip["source_end"]) * 1_000_000)
        for cue in clip.get("transcript_cues", []):
            start = round((segment_start + float(cue.get("start", 0))) * 1_000_000)
            end = round((segment_start + float(cue.get("end", 0))) * 1_000_000)
            start, end = max(start, clip_start), min(end, clip_end)
            text = str(cue.get("text", "")).strip()
            if end <= start or not text:
                continue
            evidence.append(
                {
                    "clip_id": clip_id,
                    "source_id": source_id,
                    "source_start_us": start,
                    "source_end_us": end,
                    "evidence": {
                        "text": text,
                        "asr_confidence": cue.get("confidence"),
                    },
                }
            )
    return evidence


def parse_speech_decisions(
    payload: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[SpeechDecision]:
    raw = payload.get("decisions")
    if not isinstance(raw, list) or len(raw) != len(evidence):
        raise ValueError("speech decision node must decide every ASR evidence span")
    result: list[SpeechDecision] = []
    for expected, item in zip(evidence, raw, strict=True):
        if not isinstance(item, dict):
            raise ValueError("speech decision must be an object")
        decision = SpeechDecision.model_validate(
            {
                **expected,
                "decision": item.get("decision"),
                "reason": item.get("reason"),
                "protect": bool(item.get("protect", item.get("decision") == "KEEP")),
            }
        )
        result.append(decision)
    return result


def refine_speech_clips(
    clips: list[dict[str, Any]], decisions: list[SpeechDecision]
) -> list[dict[str, Any]]:
    SpeechEditingPlan(decisions=decisions).require_resolved()
    by_clip: dict[str, list[SpeechDecision]] = {}
    for item in decisions:
        by_clip.setdefault(item.clip_id, []).append(item)
    refined: list[dict[str, Any]] = []
    for clip in clips:
        clip_id = str(clip["clip_id"])
        source_id = str(clip.get("media_id") or clip.get("segment_id"))
        clip_start = round(float(clip["source_start"]) * 1_000_000)
        clip_end = round(float(clip["source_end"]) * 1_000_000)
        relevant = by_clip.get(clip_id, [])
        if any(item.source_id != source_id for item in relevant):
            raise ValueError("speech decision source identity differs from its clip")
        deletes = _merged_ranges(
            [
                (max(clip_start, item.source_start_us), min(clip_end, item.source_end_us))
                for item in relevant
                if item.decision == SpeechDecisionKind.DELETE
            ]
        )
        keeps = _subtract_ranges(clip_start, clip_end, deletes)
        if not keeps:
            continue
        for piece_index, (start, end) in enumerate(keeps):
            piece = deepcopy(clip)
            piece["clip_id"] = (
                clip_id
                if piece_index == 0
                else str(uuid5(NAMESPACE_URL, f"{clip_id}:{start}:{end}"))
            )
            piece["source_start"] = start / 1_000_000
            piece["source_end"] = end / 1_000_000
            piece["transition"] = clip.get("transition", "cut") if end == clip_end else "cut"
            protected = []
            for decision in relevant:
                if (
                    decision.decision == SpeechDecisionKind.KEEP
                    and decision.protect
                    and start <= decision.source_start_us < decision.source_end_us <= end
                ):
                    protected.append(
                        {
                            "start_us": decision.source_start_us,
                            "end_us": decision.source_end_us,
                            "reason": "protected_speech",
                            "evidence": decision.evidence,
                        }
                    )
            piece["protected_ranges"] = protected
            refined.append(piece)
    if not refined:
        raise ValueError("speech decisions removed the entire video timeline")
    return refined


def _merged_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(item for item in ranges if item[1] > item[0]):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract_ranges(start: int, end: int, deletes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    cursor = start
    for delete_start, delete_end in deletes:
        if delete_start > cursor:
            result.append((cursor, delete_start))
        cursor = max(cursor, delete_end)
    if cursor < end:
        result.append((cursor, end))
    return result
