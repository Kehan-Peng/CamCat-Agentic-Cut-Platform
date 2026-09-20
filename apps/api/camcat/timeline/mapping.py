from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from camcat.timeline.frames import round_ratio
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
        *,
        track_id: str,
        segment_id: str,
        source_id: str,
        source_time_us: int,
        policy: ProjectionPolicy = ProjectionPolicy.ERROR,
    ) -> int:
        matches = [
            segment
            for segment in self.segments
            if segment.track_id == track_id
            and segment.segment_id == segment_id
            and segment.source_id == source_id
        ]
        if len(matches) != 1:
            raise TimelineValidationError(
                "source mapping requires an exact track/segment/source identity: "
                f"{track_id}/{segment_id}/{source_id}"
            )
        segment = matches[0]
        start = segment.visible_source_start_us
        end = start + segment.visible_source_duration_us
        if start <= source_time_us <= end:
            source_delta = min(source_time_us, end) - start
            speed = Fraction(str(segment.speed))
            target_delta = round_ratio(
                source_delta * self.fps_num * speed.denominator,
                1_000_000 * self.fps_den * speed.numerator,
            )
            return min(
                segment.timeline_start_frame + target_delta,
                segment.timeline_start_frame + segment.timeline_duration_frames,
            )
        if policy == ProjectionPolicy.SNAP_NEXT and source_time_us < start:
            return segment.timeline_start_frame
        if policy == ProjectionPolicy.SNAP_PREVIOUS and source_time_us > end:
            return segment.timeline_start_frame + segment.timeline_duration_frames
        raise TimelineValidationError(
            f"source timestamp is outside the selected occurrence: {segment_id}@{source_time_us}"
        )
