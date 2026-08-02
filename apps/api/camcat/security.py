from __future__ import annotations

import hmac


class AuthenticationError(RuntimeError):
    pass


def resolve_owner(
    *,
    security_mode: str,
    local_user_id: str,
    claimed_user_id: str | None,
    authenticated_user: str | None,
    proxy_secret: str | None,
    expected_proxy_secret: str | None,
) -> str:
    if security_mode == "local-single-user":
        return local_user_id
    if security_mode != "multi-user":
        raise AuthenticationError("unsupported security mode")
    if not authenticated_user or not expected_proxy_secret or not proxy_secret:
        raise AuthenticationError("trusted proxy authentication is required")
    if not hmac.compare_digest(proxy_secret, expected_proxy_secret):
        raise AuthenticationError("trusted proxy authentication failed")
    _ = claimed_user_id
    return authenticated_user[:128]


def authorize_library_import(
    security_mode: str, supplied_admin_key: str | None, expected_admin_key: str | None
) -> bool:
    if security_mode == "local-single-user":
        return True
    return bool(
        supplied_admin_key
        and expected_admin_key
        and hmac.compare_digest(supplied_admin_key, expected_admin_key)
    )
