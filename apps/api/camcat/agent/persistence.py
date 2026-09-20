from __future__ import annotations

from typing import Any
from uuid import UUID

from camcat.database import SessionLocal
from camcat.domain.commands import DomainEditCommand
from camcat.repositories import StateRepository


class StatePersistenceService:
    """Side-effect boundary used only by the LangGraph persistence node."""

    def persist(
        self,
        *,
        session_id: str,
        owner_id: str,
        base_version: int,
        commands: list[DomainEditCommand],
        reason: str,
    ) -> tuple[int, dict[str, Any]]:
        with SessionLocal() as db:
            state, _ = StateRepository(db).apply_commands(
                session_id=UUID(session_id),
                owner_id=owner_id,
                base_version=base_version,
                commands=commands,
                actor="camcat-agent",
                reason=reason,
            )
            return state.version, state.document
