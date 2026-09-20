from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpeechDecisionKind(StrEnum):
    KEEP = "KEEP"
    DELETE = "DELETE"
    CHECK = "CHECK"


class SpeechDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    decision: SpeechDecisionKind
    source_start_us: int = Field(ge=0)
    source_end_us: int = Field(gt=0)
    reason: str = Field(min_length=1)
    evidence: dict[str, Any] = Field(default_factory=dict)
    protect: bool = False

    @model_validator(mode="after")
    def ordered(self) -> SpeechDecision:
        if self.source_end_us <= self.source_start_us:
            raise ValueError("speech decision range must have positive duration")
        if self.protect and self.decision != SpeechDecisionKind.KEEP:
            raise ValueError("only KEEP speech can define a protected range")
        return self


class SpeechEditingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow: str = "speech-heavy"
    decisions: list[SpeechDecision]

    def require_resolved(self) -> None:
        pending = [item for item in self.decisions if item.decision == SpeechDecisionKind.CHECK]
        if pending:
            raise ValueError(f"{len(pending)} CHECK decision(s) remain unresolved")


def protected_ranges_from_speech(plan: SpeechEditingPlan) -> list[dict[str, Any]]:
    plan.require_resolved()
    return [
        {
            "start_us": item.source_start_us,
            "end_us": item.source_end_us,
            "reason": "protected_speech",
            "evidence": item.evidence,
        }
        for item in plan.decisions
        if item.decision == SpeechDecisionKind.KEEP and item.protect
    ]
