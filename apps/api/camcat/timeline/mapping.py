from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from camcat.timeline.schemas import CompiledVideoSegment
from camcat.timeline.validator import TimelineValidationError


class ProjectionPolicy(StrEnum):
    ERROR = "error"
    SNAP_NEXT = "snap_next"
    SNAP_PREVIOUS = "snap_previous"


@dataclass(frozen=True, slots=True)
class SourceTimeMapper:
    segments: tuple[CompiledVideoSegment, ...]
    fps_num: int
    fps_den: int

    @classmethod
    def from_segments(
        cls,
        segments: list[CompiledVideoSegment],
        *,
        fps_num: int,
        fps_den: int,
    ) -> SourceTimeMapper:
        return cls(tuple(segments), fps_num, fps_den)

    def project(
        self,
        source_id: str,
        source_time_us: int,
        policy: ProjectionPolicy = ProjectionPolicy.ERROR,
        *,
        clip_id: str | None = None,
    ) -> int:
        matches = [
            segment
            for segment in self.segments
            if segment.source_id == source_id and (clip_id is None or segment.clip_id == clip_id)
        ]
        if clip_id is None and len(matches) > 1:
            raise TimelineValidationError(
                f"source timestamp mapping is ambiguous without clip_id: {source_id}"
            )
        for segment in matches:
            start = segment.source_start_us
            end = start + segment.source_duration_us
            if start <= source_time_us <= end:
                source_delta = min(source_time_us, end) - start
                speed = Fraction(str(segment.speed))
                numerator = source_delta * self.fps_num * speed.denominator
                denominator = 1_000_000 * self.fps_den * speed.numerator
                target_delta_frames = (2 * numerator + denominator) // (2 * denominator)
                return min(
                    segment.target_start_frame + target_delta_frames,
                    segment.target_start_frame + segment.target_duration_frames,
                )
        if policy == ProjectionPolicy.SNAP_NEXT:
            next_segments = [item for item in matches if source_time_us < item.source_start_us]
            if next_segments:
                return min(next_segments, key=lambda item: item.source_start_us).target_start_frame
        if policy == ProjectionPolicy.SNAP_PREVIOUS:
            previous = [
                item
                for item in matches
                if source_time_us > item.source_start_us + item.source_duration_us
            ]
            if previous:
                selected = max(previous, key=lambda item: item.source_start_us)
                return selected.target_start_frame + selected.target_duration_frames
        raise TimelineValidationError(
            f"source timestamp is inside a deleted source range: {source_id}@{source_time_us}"
        )
