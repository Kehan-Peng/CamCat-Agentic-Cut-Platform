from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True, slots=True)
class SegmentBoundary:
    start: float
    end: float
    trigger_type: str


def build_segments(
    *,
    duration: float,
    fixed_window: float = 5.0,
    scene_cuts: list[float] | tuple[float, ...] = (),
    minimum_duration: float = 3.0,
    event_times: list[float] | tuple[float, ...] = (),
    event_context_seconds: float = 4.0,
) -> list[SegmentBoundary]:
    if duration <= 0 or fixed_window <= 0 or minimum_duration <= 0 or event_context_seconds <= 0:
        raise ValueError("duration and window sizes must be positive")

    # Scene boundaries are authoritative. Tiny scenes are merged before any fixed
    # windows are introduced, so the default 5s/3s settings cannot suppress cuts.
    cuts = sorted({round(float(value), 6) for value in scene_cuts if 0 < float(value) < duration})
    points = [0.0, *cuts, round(duration, 6)]
    scenes = [[start, end] for start, end in zip(points, points[1:], strict=False)]
    while len(scenes) > 1:
        short_index = next(
            (index for index, (start, end) in enumerate(scenes) if end - start < minimum_duration),
            None,
        )
        if short_index is None:
            break
        if short_index == 0:
            scenes[1][0] = scenes[0][0]
            scenes.pop(0)
        else:
            scenes[short_index - 1][1] = scenes[short_index][1]
            scenes.pop(short_index)

    segments: list[SegmentBoundary] = []
    for scene_start, scene_end in scenes:
        scene_duration = scene_end - scene_start
        window_count = max(1, ceil(scene_duration / fixed_window))
        step = scene_duration / window_count
        for index in range(window_count):
            start = round(scene_start + index * step, 6)
            end = round(
                scene_end if index == window_count - 1 else scene_start + (index + 1) * step, 6
            )
            touches_scene_cut = scene_start in cuts or scene_end in cuts
            trigger = "scene_cut" if window_count == 1 and touches_scene_cut else "fixed"
            segments.append(SegmentBoundary(start=start, end=end, trigger_type=trigger))

    for raw_event in sorted(set(float(value) for value in event_times)):
        if not 0 <= raw_event <= duration:
            continue
        start = round(max(0.0, raw_event - event_context_seconds), 6)
        end = round(min(duration, raw_event + event_context_seconds), 6)
        if end > start and not any(
            item.start == start and item.end == end and item.trigger_type == "event_context"
            for item in segments
        ):
            segments.append(SegmentBoundary(start=start, end=end, trigger_type="event_context"))
    return segments
