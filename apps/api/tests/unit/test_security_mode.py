import pytest
from camcat.security import AuthenticationError, authorize_library_import, resolve_owner


def test_local_mode_ignores_browser_supplied_identity() -> None:
    assert (
        resolve_owner(
            security_mode="local-single-user",
            local_user_id="local-owner",
            claimed_user_id="attacker",
            authenticated_user=None,
            proxy_secret=None,
            expected_proxy_secret=None,
        )
        == "local-owner"
    )


def test_multi_user_mode_requires_trusted_proxy_identity() -> None:
    with pytest.raises(AuthenticationError):
        resolve_owner(
            security_mode="multi-user",
            local_user_id="local-owner",
            claimed_user_id="attacker",
            authenticated_user="real-user",
            proxy_secret="wrong",
            expected_proxy_secret="secret",
        )

    assert (
        resolve_owner(
            security_mode="multi-user",
            local_user_id="local-owner",
            claimed_user_id="attacker",
            authenticated_user="real-user",
            proxy_secret="secret",
            expected_proxy_secret="secret",
        )
        == "real-user"
    )


def test_multi_user_library_import_requires_admin_key() -> None:
    assert authorize_library_import("local-single-user", None, None)
    assert not authorize_library_import("multi-user", "wrong", "admin-secret")
    assert authorize_library_import("multi-user", "admin-secret", "admin-secret")
