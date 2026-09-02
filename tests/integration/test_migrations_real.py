from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from camcat.config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.integration


def test_clean_database_upgrade_downgrade_upgrade() -> None:
    root = Path(__file__).resolve().parents[2]
    base_url = make_url(get_settings().database_url)
    database_name = f"camcat_migration_{uuid4().hex}"
    admin_url = base_url.set(database="postgres")
    test_url = base_url.set(database=database_name)
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    environment = {**os.environ, "CAMCAT_DATABASE_URL": test_url.render_as_string(False)}
    try:
        for command in (("upgrade", "head"), ("downgrade", "base"), ("upgrade", "head")):
            subprocess.run(
                [sys.executable, "-m", "alembic", *command],
                cwd=root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))
        admin.dispose()
