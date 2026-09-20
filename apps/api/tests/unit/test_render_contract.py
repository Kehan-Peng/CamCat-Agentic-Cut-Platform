from camcat.schemas import RenderRequest


def test_render_uses_only_execution_profile() -> None:
    request = RenderRequest(base_version=1)
    assert request.quality_profile == "standard"
    assert "resolution" not in request.model_fields_set
    assert "fps" not in request.model_fields_set


def test_render_rejects_timeline_geometry_overrides() -> None:
    assert RenderRequest.model_config["extra"] == "forbid"
