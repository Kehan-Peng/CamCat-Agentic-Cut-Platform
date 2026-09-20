from __future__ import annotations

import pytest
from camcat.editing.speech import (
    SpeechDecision,
    SpeechDecisionKind,
    SpeechEditingPlan,
    protected_ranges_from_speech,
)


def test_keep_delete_check_preserves_evidence_and_protection() -> None:
    plan = SpeechEditingPlan(
        decisions=[
            SpeechDecision(
                clip_id="clip-a",
                source_id="media-a",
                decision=SpeechDecisionKind.KEEP,
                source_start_us=0,
                source_end_us=500_000,
                reason="key_point",
                evidence={"text": "important", "asr_confidence": 0.94},
                protect=True,
            ),
            SpeechDecision(
                clip_id="clip-a",
                source_id="media-a",
                decision=SpeechDecisionKind.DELETE,
                source_start_us=500_000,
                source_end_us=800_000,
                reason="repeated_statement",
                evidence={"text": "repeat"},
            ),
        ]
    )
    plan.require_resolved()
    protected = protected_ranges_from_speech(plan)
    assert protected == [
        {
            "start_us": 0,
            "end_us": 500_000,
            "reason": "protected_speech",
            "evidence": {"text": "important", "asr_confidence": 0.94},
        }
    ]


def test_unresolved_check_blocks_compilation_handoff() -> None:
    plan = SpeechEditingPlan(
        decisions=[
            SpeechDecision(
                clip_id="clip-a",
                source_id="media-a",
                decision=SpeechDecisionKind.CHECK,
                source_start_us=0,
                source_end_us=300_000,
                reason="semantic_ambiguity",
                evidence={"text": "maybe"},
            )
        ]
    )
    with pytest.raises(ValueError, match="CHECK"):
        plan.require_resolved()
