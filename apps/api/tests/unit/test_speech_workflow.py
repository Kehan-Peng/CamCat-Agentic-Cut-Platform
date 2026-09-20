from __future__ import annotations

import pytest
from camcat.editing.speech import SpeechDecision, SpeechDecisionKind
from camcat.editing.speech_workflow import (
    collect_speech_evidence,
    is_speech_heavy,
    refine_speech_clips,
)


def clip() -> dict[str, object]:
    return {
        "clip_id": "clip-a",
        "segment_id": "segment-a",
        "media_id": "media-a",
        "origin": "source",
        "segment_start": 10.0,
        "source_start": 10.0,
        "source_end": 14.0,
        "transition": "cut",
        "transcript_cues": [
            {"start": 0.0, "end": 1.0, "text": "关键论点", "confidence": 0.95},
            {"start": 1.0, "end": 2.0, "text": "重复内容", "confidence": 0.9},
            {"start": 2.0, "end": 4.0, "text": "结论", "confidence": 0.93},
        ],
    }


def test_speech_workflow_is_opt_in_by_content_type() -> None:
    assert is_speech_heavy("剪一段口播教程", {"style": "tutorial"})
    assert not is_speech_heavy("做一个纯音乐风景混剪", {"style": "cinematic"})


def test_evidence_is_source_bound_and_delete_refines_clip() -> None:
    evidence = collect_speech_evidence([clip()])
    assert evidence[1]["source_start_us"] == 11_000_000
    assert evidence[1]["evidence"]["text"] == "重复内容"
    decisions = [
        SpeechDecision(
            clip_id="clip-a",
            source_id="media-a",
            decision=SpeechDecisionKind.KEEP,
            source_start_us=10_000_000,
            source_end_us=11_000_000,
            reason="key_point",
            evidence={"text": "关键论点"},
            protect=True,
        ),
        SpeechDecision(
            clip_id="clip-a",
            source_id="media-a",
            decision=SpeechDecisionKind.DELETE,
            source_start_us=11_000_000,
            source_end_us=12_000_000,
            reason="repeated_statement",
            evidence={"text": "重复内容"},
        ),
        SpeechDecision(
            clip_id="clip-a",
            source_id="media-a",
            decision=SpeechDecisionKind.KEEP,
            source_start_us=12_000_000,
            source_end_us=14_000_000,
            reason="conclusion",
            evidence={"text": "结论"},
            protect=True,
        ),
    ]

    refined = refine_speech_clips([clip()], decisions)

    assert [(item["source_start"], item["source_end"]) for item in refined] == [
        (10.0, 11.0),
        (12.0, 14.0),
    ]
    assert refined[0]["clip_id"] == "clip-a"
    assert refined[1]["clip_id"] != "clip-a"
    assert refined[0]["protected_ranges"][0]["reason"] == "protected_speech"


def test_check_decision_blocks_boundary_refinement() -> None:
    with pytest.raises(ValueError, match="CHECK"):
        refine_speech_clips(
            [clip()],
            [
                SpeechDecision(
                    clip_id="clip-a",
                    source_id="media-a",
                    decision=SpeechDecisionKind.CHECK,
                    source_start_us=10_000_000,
                    source_end_us=11_000_000,
                    reason="uncertain_cut",
                    evidence={"text": "ambiguous"},
                )
            ],
        )
