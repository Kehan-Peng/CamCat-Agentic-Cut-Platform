from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


class MediaCommandError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    duration: float
    width: int
    height: int
    has_audio: bool


def shot_signature(thumbnail: Path) -> str:
    return hashlib.sha256(thumbnail.read_bytes()).hexdigest()[:24]


def measure_visual_quality(path: Path) -> float:
    """Return a bounded, real-media quality signal using FFmpeg's blur detector."""
    result = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            "scale=320:-2,blurdetect=block_width=32:block_height=32:block_pct=80",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    values = [float(value) for value in re.findall(r"blur mean:\s*([0-9.]+)", result.stderr)]
    if not values:
        return 0.6
    # blurdetect is higher for blurrier frames; map it conservatively into 0..1.
    blur = sum(values) / len(values)
    return round(max(0.05, min(1.0, 1.0 - blur / 20.0)), 4)


def probe(path: Path) -> MediaMetadata:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if video is None:
        raise MediaCommandError("uploaded media has no video stream")
    duration = float(payload.get("format", {}).get("duration") or video.get("duration") or 0)
    if duration <= 0:
        raise MediaCommandError("uploaded media duration is unavailable")
    return MediaMetadata(
        duration=duration,
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        has_audio=any(item.get("codec_type") == "audio" for item in streams),
    )


def detect_scene_cuts(path: Path, threshold: float = 0.35) -> list[float]:
    result = _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-filter:v",
            f"select='gt(scene,{threshold})',showinfo",
            "-an",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise MediaCommandError(result.stderr[-2000:])
    return sorted({float(value) for value in re.findall(r"pts_time:([0-9.]+)", result.stderr)})


def extract_clip(source: Path, target: Path, *, start: float, end: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(target),
        ]
    )


def extract_thumbnail(source: Path, target: Path, *, at: float) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-ss",
            f"{at:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2",
            str(target),
        ]
    )


def extract_audio(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "mp3",
            str(target),
        ]
    )


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise MediaCommandError(
            f"command {args[0]} failed ({result.returncode}): {result.stderr[-4000:]}"
        )
    return result
