from camcat.schemas import RenderRequest


def test_render_defaults_to_session_selected_aspect_ratio() -> None:
    assert RenderRequest(base_version=1).resolution is None
