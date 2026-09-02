from __future__ import annotations

from camcat.models import JobKind
from camcat.schemas import SourceMediaReference


def test_transient_source_has_no_asset_or_segment_database_identifier() -> None:
    source = SourceMediaReference(
        media_id="source-1",
        filename="raw.mov",
        content_type="video/quicktime",
        storage_key="temporary/user/batch/source-1/raw.mov",
        expires_at="2026-07-19T12:30:00Z",
    )

    payload = source.model_dump()
    assert "asset_id" not in payload
    assert "segment_id" not in payload
    assert JobKind.ANALYZE_SOURCE.value == "analyze_source"
