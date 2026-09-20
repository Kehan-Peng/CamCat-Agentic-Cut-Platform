from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, cast

from camcat.timeline.schemas import MediaFingerprint


class MediaFingerprintError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_json(path: Path, *, count_frames: bool = False) -> dict[str, Any]:
    args = ["ffprobe", "-v", "error"]
    if count_frames:
        args.append("-count_frames")
    args += ["-show_streams", "-show_format", "-of", "json", str(path)]
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise MediaFingerprintError(f"ffprobe failed: {result.stderr[-2000:]}")
    try:
        return cast(dict[str, Any], json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        raise MediaFingerprintError("ffprobe returned invalid JSON") from exc


def fingerprint_media(path: Path, *, media_id: str, storage_key: str) -> MediaFingerprint:
    resolved = path.resolve(strict=True)
    before = resolved.stat()
    if not resolved.is_file() or before.st_size <= 0:
        raise MediaFingerprintError("media source must be a non-empty regular file")
    payload = probe_json(resolved)
    streams = payload.get("streams", [])
    video = next(
        (
            item
            for item in streams
            if item.get("codec_type") == "video"
            and not item.get("disposition", {}).get("attached_pic")
        ),
        None,
    )
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video is None and audio is None:
        raise MediaFingerprintError("media has neither a video nor an audio stream")
    duration = float(
        payload.get("format", {}).get("duration")
        or (video or {}).get("duration")
        or (audio or {}).get("duration")
        or 0
    )
    if duration <= 0:
        raise MediaFingerprintError("media duration is unavailable")
    checksum = sha256_file(resolved)
    after = resolved.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise MediaFingerprintError("media changed while it was fingerprinted")
    return MediaFingerprint(
        media_id=media_id,
        storage_key=storage_key,
        local_path=str(resolved),
        sha256=checksum,
        file_size=before.st_size,
        duration_us=round(duration * 1_000_000),
        width=int((video or {}).get("width") or 0),
        height=int((video or {}).get("height") or 0),
        video_codec=(video or {}).get("codec_name"),
        audio_codec=(audio or {}).get("codec_name"),
    )


def verify_media_fingerprint(fingerprint: MediaFingerprint) -> None:
    path = Path(fingerprint.local_path)
    if not path.is_file() or path.is_symlink():
        raise MediaFingerprintError(
            f"source fingerprint target is unavailable: {fingerprint.media_id}"
        )
    info = path.stat()
    if info.st_size != fingerprint.file_size or sha256_file(path) != fingerprint.sha256:
        raise MediaFingerprintError(f"source fingerprint changed: {fingerprint.media_id}")
    if fingerprint.video_codec or fingerprint.audio_codec:
        payload = probe_json(path)
        duration = float(payload.get("format", {}).get("duration") or 0)
        if abs(round(duration * 1_000_000) - fingerprint.duration_us) > 100_000:
            raise MediaFingerprintError(
                f"source fingerprint duration changed: {fingerprint.media_id}"
            )
