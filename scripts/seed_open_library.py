#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

from camcat.config import get_settings
from camcat.services.object_store import ObjectStore
from camcat.services.remote_media import download_remote_media

PIXABAY_DOCUMENTED_SAMPLE: dict[str, object] = {
    "download_url": "https://cdn.pixabay.com/video/2015/08/08/125-135736646_medium.mp4",
    "source_url": "https://pixabay.com/videos/id-125/",
    "license_name": "Pixabay Content License",
    "filename": "pixabay-125-yellow-flowers.mp4",
}


def api_json(url: str, payload: dict[str, object], user: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-User-Id": user},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return cast(dict[str, Any], json.load(response))


def pixabay_candidates(
    api_key: str, query: str, count: int, max_duration: int
) -> list[dict[str, object]]:
    params = urllib.parse.urlencode(
        {
            "key": api_key,
            "q": query,
            "video_type": "film",
            "safesearch": "true",
            "order": "popular",
            "per_page": min(20, max(3, count * 3)),
        }
    )
    with urllib.request.urlopen(
        f"https://pixabay.com/api/videos/?{params}", timeout=60
    ) as response:
        payload = cast(dict[str, Any], json.load(response))
    result: list[dict[str, object]] = []
    for video in payload.get("hits", []):
        if int(video.get("duration", 0)) > max_duration:
            continue
        rendition = video.get("videos", {}).get("small") or video.get("videos", {}).get("medium")
        if not rendition or not rendition.get("url"):
            continue
        tag_slug = "-".join(video.get("tags", "").split(", ")[:3])
        result.append(
            {
                "download_url": rendition["url"],
                "source_url": video["pageURL"],
                "license_name": "Pixabay Content License",
                "filename": f"pixabay-{video['id']}-{tag_slug}.mp4",
            }
        )
        if len(result) >= count:
            break
    return result


def seed_audio(manifest_path: Path) -> list[dict[str, Any]]:
    settings = get_settings()
    store = ObjectStore(settings)
    store.ensure_bucket()
    catalog = cast(list[dict[str, Any]], json.loads(manifest_path.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory(prefix="camcat-audio-") as directory:
        for item in catalog:
            target = Path(directory) / f"{item['id']}.mp3"
            media = download_remote_media(
                item["download_url"],
                target,
                maximum_bytes=25 * 1024 * 1024,
                accepted_content_prefixes=("audio/", "application/octet-stream"),
            )
            store.upload_file(target, item["storage_key"], media.content_type)
    public_catalog = [
        {key: value for key, value in item.items() if key != "download_url"} for item in catalog
    ]
    store.write_json("library/audio/catalog.json", public_catalog)
    return public_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed CamCat with a small real open media library")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--user", default="camcat-library")
    parser.add_argument("--query", default="travel nature city")
    parser.add_argument("--count", type=int, default=2)
    parser.add_argument("--max-duration", type=int, default=20)
    parser.add_argument("--audio-manifest", default="docs/open-audio-library.json", type=Path)
    args = parser.parse_args()

    key = os.environ.get("PIXABAY_API_KEY") or os.environ.get("CAMCAT_PIXABAY_API_KEY")
    videos: list[dict[str, object]] = (
        pixabay_candidates(key, args.query, args.count, args.max_duration)
        if key
        else ([PIXABAY_DOCUMENTED_SAMPLE] if args.count > 0 else [])
    )
    for video in videos:
        print(
            json.dumps(
                api_json(f"{args.api.rstrip('/')}/api/v1/videos/import", video, args.user),
                ensure_ascii=False,
            )
        )
    audio = seed_audio(args.audio_manifest)
    print(json.dumps({"audio_seeded": len(audio)}, ensure_ascii=False))
    if not key:
        print(
            "PIXABAY_API_KEY is absent; imported the real sample published in Pixabay API docs.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
