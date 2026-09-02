import pytest
from camcat.config import Settings
from camcat.security import AuthenticationError, authorize_library_import, resolve_owner
from pydantic import ValidationError


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


def test_runtime_configuration_rejects_example_provider_credentials() -> None:
    with pytest.raises(ValidationError, match="placeholder provider configuration"):
        Settings(
            _env_file=None,
            environment="development",
            embedding_base_url="https://change-me.example.com",
            embedding_api_key="change-me",
            reranker_base_url="https://change-me.example.com",
            reranker_api_key="change-me",
            llm_base_url="https://change-me.example.com",
            llm_api_key="change-me",
            asr_base_url="https://change-me.example.com",
            asr_api_key="change-me",
        )


def test_integration_mode_can_boot_without_contacting_external_providers() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        embedding_base_url="http://provider.invalid",
        embedding_api_key="integration-placeholder",
        reranker_base_url="http://provider.invalid",
        reranker_api_key="integration-placeholder",
        llm_base_url="http://provider.invalid",
        llm_api_key="integration-placeholder",
        asr_base_url="http://provider.invalid",
        asr_api_key="integration-placeholder",
    )

    assert settings.environment == "test"
