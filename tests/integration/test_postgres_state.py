from __future__ import annotations

from uuid import uuid4

import pytest
from camcat.database import SessionLocal
from camcat.domain.state_patch import PatchConflict
from camcat.repositories import StateRepository

pytestmark = pytest.mark.integration


def test_real_postgres_compare_and_swap_and_compensating_rollback() -> None:
    owner = f"integration-{uuid4()}"
    with SessionLocal() as first_db:
        session, initial = StateRepository(first_db).create(owner_id=owner, goal="初始版本")
        session_id = session.id

    with SessionLocal() as first_db, SessionLocal() as stale_db:
        first = StateRepository(first_db)
        stale = StateRepository(stale_db)
        updated = first.apply(
            session_id=session_id,
            owner_id=owner,
            base_version=initial.version,
            operations=[{"op": "replace", "path": "/goal", "value": "并发胜者"}],
            actor=owner,
            reason="first writer",
        )
        assert updated.version == 2
        with pytest.raises(PatchConflict) as conflict:
            stale.apply(
                session_id=session_id,
                owner_id=owner,
                base_version=1,
                operations=[{"op": "replace", "path": "/goal", "value": "过期写入"}],
                actor=owner,
                reason="stale writer",
            )
        assert conflict.value.current_version == 2

    with SessionLocal() as db:
        repository = StateRepository(db)
        rolled_back = repository.rollback(
            session_id=session_id,
            owner_id=owner,
            base_version=2,
            target_version=1,
        )
        assert rolled_back.version == 3
        assert rolled_back.document["goal"] == "初始版本"
