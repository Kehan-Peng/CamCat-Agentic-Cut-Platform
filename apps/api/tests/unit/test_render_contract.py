from camcat.schemas import RenderRequest


def test_render_defaults_to_session_selected_aspect_ratio() -> None:
    assert RenderRequest(base_version=1).resolution is None
    assert RenderRequest(base_version=1).fps == 30


def test_render_profile_supports_explicit_frame_rates() -> None:
    assert RenderRequest(base_version=1, fps=24).fps == 24
    assert RenderRequest(base_version=1, fps=60).fps == 60
