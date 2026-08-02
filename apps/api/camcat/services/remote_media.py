from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx


class UnsafeRemoteMediaUrl(ValueError):
    pass


AddressResolver = Callable[..., list[tuple[Any, ...]]]


@dataclass(frozen=True, slots=True)
class RemoteDownload:
    size_bytes: int
    content_type: str
    final_url: str


def validate_remote_media_url(url: str, *, resolver: AddressResolver = socket.getaddrinfo) -> str:
    """Reject non-public download targets before every outbound media request."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise UnsafeRemoteMediaUrl("远程素材只允许公网 HTTPS 地址")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeRemoteMediaUrl("远程素材地址不能包含登录凭证")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise UnsafeRemoteMediaUrl("远程素材端口无效") from exc
    if port != 443:
        raise UnsafeRemoteMediaUrl("远程素材只允许标准 HTTPS 端口")

    try:
        literal_ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None and not literal_ip.is_global:
        raise UnsafeRemoteMediaUrl("远程素材不能指向内网、本机或保留地址")

    try:
        addresses = resolver(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeRemoteMediaUrl("远程素材域名无法解析") from exc
    if not addresses:
        raise UnsafeRemoteMediaUrl("远程素材域名没有可用地址")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise UnsafeRemoteMediaUrl("远程素材不能指向内网、本机或保留地址")
    return url


def download_remote_media(
    url: str,
    target: Path,
    *,
    maximum_bytes: int,
    timeout_seconds: float = 60.0,
    maximum_redirects: int = 5,
    accepted_content_prefixes: tuple[str, ...] = ("video/",),
) -> RemoteDownload:
    """Download a public video while validating every redirect target."""
    current = url
    target.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
        for redirect_count in range(maximum_redirects + 1):
            validate_remote_media_url(current)
            with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location or redirect_count >= maximum_redirects:
                        raise UnsafeRemoteMediaUrl("远程素材重定向无效或次数过多")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if not content_type.startswith(accepted_content_prefixes):
                    raise UnsafeRemoteMediaUrl("远程地址返回的媒体类型不受支持")
                size = 0
                try:
                    with target.open("wb") as output:
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > maximum_bytes:
                                raise UnsafeRemoteMediaUrl("远程素材超过上传大小限制")
                            output.write(chunk)
                except Exception:
                    target.unlink(missing_ok=True)
                    raise
                if size == 0:
                    target.unlink(missing_ok=True)
                    raise UnsafeRemoteMediaUrl("远程视频内容为空")
                return RemoteDownload(size, content_type, current)
    raise UnsafeRemoteMediaUrl("远程素材下载失败")
