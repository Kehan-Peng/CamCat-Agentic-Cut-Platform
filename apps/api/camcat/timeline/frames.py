from __future__ import annotations


def round_ratio(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise ValueError("frame ratio must be nonnegative")
    return (2 * numerator + denominator) // (2 * denominator)


def us_to_frame(microseconds: int, fps_num: int, fps_den: int) -> int:
    return round_ratio(microseconds * fps_num, 1_000_000 * fps_den)


def frame_to_us(frames: int, fps_num: int, fps_den: int) -> int:
    return round_ratio(frames * 1_000_000 * fps_den, fps_num)


def us_range_to_frames(
    start_us: int, duration_us: int, fps_num: int, fps_den: int
) -> tuple[int, int]:
    start = us_to_frame(start_us, fps_num, fps_den)
    end = us_to_frame(start_us + duration_us, fps_num, fps_den)
    if end <= start:
        raise ValueError("semantic interval is shorter than one timeline frame")
    return start, end - start
