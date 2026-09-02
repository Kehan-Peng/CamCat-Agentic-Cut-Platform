from __future__ import annotations

import socket

import pytest
from camcat.services.remote_media import UnsafeRemoteMediaUrl, validate_remote_media_url


def public_resolver(
    _host: str, _port: int, *, type: socket.SocketKind
) -> list[tuple[socket.AddressFamily, socket.SocketKind, int, str, tuple[str, int]]]:
    assert type == socket.SOCK_STREAM
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]


def private_resolver(
    _host: str, _port: int, *, type: socket.SocketKind
) -> list[tuple[socket.AddressFamily, socket.SocketKind, int, str, tuple[str, int]]]:
    assert type == socket.SOCK_STREAM
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443))]


def test_accepts_public_https_media_url() -> None:
    url = "https://videos.pexels.com/video-files/123/clip.mp4"
    assert validate_remote_media_url(url, resolver=public_resolver) == url


@pytest.mark.parametrize(
    "url",
    [
        "http://videos.example.com/clip.mp4",
        "https://127.0.0.1/clip.mp4",
        "https://169.254.169.254/latest/meta-data",
        "https://user:password@videos.example.com/clip.mp4",
        "https://videos.example.com:8443/clip.mp4",
    ],
)
def test_rejects_unsafe_remote_media_urls(url: str) -> None:
    with pytest.raises(UnsafeRemoteMediaUrl):
        validate_remote_media_url(url, resolver=public_resolver)


def test_rejects_hostname_resolving_to_private_address() -> None:
    with pytest.raises(UnsafeRemoteMediaUrl):
        validate_remote_media_url("https://videos.example.com/clip.mp4", resolver=private_resolver)
