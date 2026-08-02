from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


def normalize_clip(
    source: Path,
    target: Path,
    *,
    width: int,
    height: int,
    transition_seconds: float = 0.18,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    metadata = probe(source)
    fade_out_start = max(0.0, metadata.duration - transition_seconds)
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        "eq=contrast=1.035:saturation=1.06:gamma=1.01,"
        f"fade=t=in:st=0:d={transition_seconds:.3f},"
        f"fade=t=out:st={fade_out_start:.3f}:d={transition_seconds:.3f},"
        "setsar=1,fps=30"
    )
    args = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-i",
        str(source),
    ]
    if not metadata.has_audio:
        args += [
            "-f",
            "lavfi",
            "-t",
            f"{metadata.duration:.3f}",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
        ]
    args += [
        "-vf",
        video_filter,
        "-map",
        "0:v:0",
        "-map",
        "0:a:0" if metadata.has_audio else "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-af",
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-shortest",
        str(target),
    ]
    _run(args)


def concat_clips(
    clips: list[Path],
    target: Path,
    *,
    subtitles: Path | None = None,
    background_music: Path | None = None,
    ambient_audio: Path | None = None,
    sound_effect: Path | None = None,
) -> None:
    if not clips:
        raise ValueError("at least one clip is required for rendering")
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = target.with_suffix(".concat.txt")
    manifest.write_text(
        "".join(f"file '{_concat_escape(path.resolve())}'\n" for path in clips), encoding="utf-8"
    )
    args = ["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", str(manifest)]
    audio_inputs: list[tuple[Path, bool, float, int]] = []
    if background_music is not None:
        audio_inputs.append((background_music, True, 0.12, 0))
    if ambient_audio is not None:
        audio_inputs.append((ambient_audio, True, 0.07, 0))
    if sound_effect is not None:
        audio_inputs.append((sound_effect, False, 0.28, 650))
    for path, loop, _volume, _delay in audio_inputs:
        if loop:
            args += ["-stream_loop", "-1"]
        args += ["-i", str(path)]
    if subtitles is not None:
        escaped = (
            str(subtitles.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        )
        args += [
            "-vf",
            (
                f"subtitles='{escaped}':force_style='Alignment=2,MarginV=120,"
                "FontName=Heiti SC,Fontsize=18,Outline=2,Shadow=0'"
            ),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
        ]
    else:
        args += ["-c:v", "copy"]
    if audio_inputs:
        filter_parts = ["[0:a]volume=1.0[dialogue]"]
        mix_labels = ["[dialogue]"]
        for index, (_path, _loop, volume, delay) in enumerate(audio_inputs, start=1):
            label = f"supplement{index}"
            delay_filter = f"adelay={delay}|{delay}," if delay else ""
            filter_parts.append(f"[{index}:a]{delay_filter}volume={volume}[{label}]")
            mix_labels.append(f"[{label}]")
        filter_parts.append(
            f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:"
            "dropout_transition=2,loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
        )
        args += [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
        ]
    args += [
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        "-shortest",
        str(target),
    ]
    try:
        _run(args)
    finally:
        manifest.unlink(missing_ok=True)


def write_srt(subtitles: list[dict[str, Any]], target: Path) -> None:
    blocks: list[str] = []
    for index, subtitle in enumerate(subtitles, start=1):
        start = _srt_time(float(subtitle["start"]))
        end = _srt_time(float(subtitle["end"]))
        text = str(subtitle["text"]).replace("\r", " ").strip()
        blocks.append(f"{index}\n{start} --> {end}\n{text}\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(blocks), encoding="utf-8")


def _srt_time(seconds: float) -> str:
    milliseconds = round(max(0.0, seconds) * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _concat_escape(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise MediaCommandError(
            f"command {args[0]} failed ({result.returncode}): {result.stderr[-4000:]}"
        )
    return result
