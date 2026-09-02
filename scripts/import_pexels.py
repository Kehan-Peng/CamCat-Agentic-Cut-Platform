#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def request_json(
    url: str, *, headers: dict[str, str], payload: dict[str, object] | None = None
) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url, headers=headers, data=body, method="POST" if body else "GET"
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import short licensed Pexels videos into CamCat")
    parser.add_argument("query", help="Pexels video search query")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--max-duration", type=int, default=20)
    parser.add_argument(
        "--orientation", choices=["landscape", "portrait", "square"], default="portrait"
    )
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--user", default="camcat-local-user")
    args = parser.parse_args()

    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        print("PEXELS_API_KEY is required", file=sys.stderr)
        return 2
    query = urllib.parse.urlencode(
        {"query": args.query, "orientation": args.orientation, "per_page": min(80, args.count * 8)}
    )
    result = request_json(
        f"https://api.pexels.com/v1/videos/search?{query}", headers={"Authorization": api_key}
    )
    candidates = [
        item
        for item in result.get("videos", [])
        if int(item.get("duration", 0)) <= args.max_duration
    ]
    imported = 0
    for video in candidates:
        files = [
            item
            for item in video.get("video_files", [])
            if item.get("file_type") == "video/mp4" and item.get("link")
        ]
        if not files:
            continue
        selected = min(
            files,
            key=lambda item: (
                abs(int(item.get("height") or 720) - 720)
                + abs(int(item.get("width") or 1280) - 1280)
            ),
        )
        payload = {
            "download_url": selected["link"],
            "source_url": video["url"],
            "license_name": "Pexels License",
            "filename": f"pexels-{video['id']}.mp4",
        }
        response = request_json(
            f"{args.api.rstrip('/')}/api/v1/videos/import",
            headers={"Content-Type": "application/json", "X-User-Id": args.user},
            payload=payload,
        )
        print(json.dumps(response, ensure_ascii=False))
        imported += 1
        if imported >= args.count:
            break
    if imported < args.count:
        print(f"Only found {imported} videos no longer than {args.max_duration}s", file=sys.stderr)
    return 0 if imported else 1


if __name__ == "__main__":
    raise SystemExit(main())
