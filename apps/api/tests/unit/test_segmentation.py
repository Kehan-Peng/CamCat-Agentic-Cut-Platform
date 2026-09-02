from camcat.media.segmentation import build_segments


def test_fixed_windows_cover_media_without_gaps() -> None:
    segments = build_segments(duration=12.5, fixed_window=5.0, scene_cuts=[])

    assert [(segment.start, segment.end) for segment in segments] == [
        (0.0, 4.166667),
        (4.166667, 8.333333),
        (8.333333, 12.5),
    ]


def test_scene_cut_splits_long_window_but_avoids_tiny_fragments() -> None:
    segments = build_segments(
        duration=10.0,
        fixed_window=10.0,
        scene_cuts=[0.2, 4.5, 9.8],
        minimum_duration=3.0,
    )

    assert [(segment.start, segment.end) for segment in segments] == [(0.0, 4.5), (4.5, 10.0)]


def test_scene_first_default_accepts_cuts_that_fixed_first_algorithm_rejected() -> None:
    segments = build_segments(
        duration=10.0,
        fixed_window=5.0,
        scene_cuts=[3.2, 6.8],
        minimum_duration=3.0,
    )

    assert [(segment.start, segment.end, segment.trigger_type) for segment in segments] == [
        (0.0, 3.2, "scene_cut"),
        (3.2, 6.8, "scene_cut"),
        (6.8, 10.0, "scene_cut"),
    ]


def test_short_scenes_merge_before_long_scenes_are_windowed() -> None:
    segments = build_segments(
        duration=14.0,
        fixed_window=5.0,
        scene_cuts=[1.0, 9.0],
        minimum_duration=3.0,
    )

    assert [(item.start, item.end) for item in segments] == [
        (0.0, 4.5),
        (4.5, 9.0),
        (9.0, 14.0),
    ]


def test_event_context_adds_bounded_overlapping_candidates() -> None:
    segments = build_segments(
        duration=20.0,
        fixed_window=10.0,
        event_times=[1.0, 10.0, 19.0],
        event_context_seconds=4.0,
    )

    contexts = [item for item in segments if item.trigger_type == "event_context"]
    assert [(item.start, item.end) for item in contexts] == [
        (0.0, 5.0),
        (6.0, 14.0),
        (15.0, 20.0),
    ]
