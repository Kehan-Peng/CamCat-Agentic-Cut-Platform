from __future__ import annotations

from typing import Any
from uuid import UUID

from camcat.database import SessionLocal
from camcat.repositories import StateRepository


class StatePersistenceService:
    """Side-effect boundary used only by the LangGraph persistence node."""

    def persist(
        self,
        *,
        session_id: str,
        owner_id: str,
        base_version: int,
        operations: list[dict[str, Any]],
        reason: str,
    ) -> tuple[int, dict[str, Any]]:
        with SessionLocal() as db:
            state = StateRepository(db).apply(
                session_id=UUID(session_id),
                owner_id=owner_id,
                base_version=base_version,
                operations=operations,
                actor="camcat-agent",
                reason=reason,
            )
            return state.version, state.document
