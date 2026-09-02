from pathlib import Path


def test_initial_migration_is_explicit_and_immutable() -> None:
    source = Path("apps/api/alembic/versions/0001_initial.py").read_text(encoding="utf-8")
    assert "metadata.create_all" not in source
    assert "metadata.drop_all" not in source
    for table in (
        "assets",
        "segments",
        "editing_sessions",
        "state_versions",
        "state_patches",
        "jobs",
        "graph_runs",
    ):
        assert f'op.create_table(\n        "{table}"' in source
