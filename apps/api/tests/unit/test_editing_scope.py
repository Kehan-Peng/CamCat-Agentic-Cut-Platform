from camcat.agent.scope import editing_retrieval_filters, needs_material_retrieval


def test_editing_agent_searches_the_whole_material_library() -> None:
    assert editing_retrieval_filters(base_asset_id="source-video") == {}


def test_title_and_subtitle_only_edits_skip_material_retrieval() -> None:
    assert needs_material_retrieval("把标题改成夏日记忆") is False
    assert needs_material_retrieval("调整字幕文案，不改镜头") is False
    assert needs_material_retrieval("重新剪辑并增加海边素材") is True
