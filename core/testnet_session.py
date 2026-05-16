from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestnetSessionJournal:
    def __init__(self, *, max_sessions: int = 500, max_checkpoints_per_session: int = 500):
        self.max_sessions = max(50, int(max_sessions))
        self.max_checkpoints_per_session = max(20, int(max_checkpoints_per_session))
        self._sessions: list[dict[str, Any]] = []
        self._session_index: dict[str, dict[str, Any]] = {}
        self._session_sequence = 0
        self._checkpoint_sequence = 0

    def start_testnet_session(
        self,
        *,
        session_id: str = "",
        environment: str = "",
        mode: str = "",
        details: Optional[dict[str, Any]] = None,
        timestamp: Optional[Any] = None,
    ) -> dict[str, Any]:
        resolved_session_id = str(session_id or "").strip()
        if not resolved_session_id:
            self._session_sequence += 1
            resolved_session_id = f"SES-{self._session_sequence}"

        existing = self._session_index.get(resolved_session_id)
        if isinstance(existing, dict):
            return dict(existing)

        session = {
            "session_id": resolved_session_id,
            "environment": str(environment or ""),
            "mode": str(mode or ""),
            "started_at": _normalize_timestamp(timestamp),
            "finished_at": "",
            "final_status": "RUNNING",
            "details": dict(details or {}),
            "checkpoints": [],
        }
        self._sessions.append(session)
        self._session_index[resolved_session_id] = session
        if len(self._sessions) > self.max_sessions:
            dropped = self._sessions.pop(0)
            self._session_index.pop(str(dropped.get("session_id", "")), None)
        return dict(session)

    def append_testnet_checkpoint(
        self,
        *,
        session_id: str,
        step: str,
        status: str,
        details: Optional[dict[str, Any]] = None,
        timestamp: Optional[Any] = None,
    ) -> dict[str, Any]:
        resolved_session_id = str(session_id or "").strip()
        session = self._session_index.get(resolved_session_id)
        if session is None:
            session = self.start_testnet_session(
                session_id=resolved_session_id or "",
                environment="unknown",
                mode="",
            )
            session = self._session_index.get(str(session.get("session_id", "")))
        if session is None:  # pragma: no cover - defensive
            return {
                "checkpoint_id": "",
                "session_id": resolved_session_id,
                "step": str(step or ""),
                "status": str(status or ""),
                "timestamp": _normalize_timestamp(timestamp),
                "details": dict(details or {}),
            }

        self._checkpoint_sequence += 1
        checkpoint = {
            "checkpoint_id": f"CP-{self._checkpoint_sequence}",
            "session_id": str(session.get("session_id", "")),
            "step": str(step or ""),
            "status": str(status or "").upper(),
            "timestamp": _normalize_timestamp(timestamp),
            "details": dict(details or {}),
        }
        checkpoints = list(session.get("checkpoints", []))
        checkpoints.append(checkpoint)
        if len(checkpoints) > self.max_checkpoints_per_session:
            checkpoints = checkpoints[-self.max_checkpoints_per_session :]
        session["checkpoints"] = checkpoints
        return dict(checkpoint)

    def finish_testnet_session(
        self,
        *,
        session_id: str,
        final_status: str = "FINISHED",
        details: Optional[dict[str, Any]] = None,
        timestamp: Optional[Any] = None,
    ) -> dict[str, Any]:
        resolved_session_id = str(session_id or "").strip()
        session = self._session_index.get(resolved_session_id)
        if session is None:
            created = self.start_testnet_session(
                session_id=resolved_session_id or "",
                environment="unknown",
                mode="",
            )
            resolved_session_id = str(created.get("session_id", ""))
            session = self._session_index.get(resolved_session_id)

        if session is None:  # pragma: no cover - defensive
            return {
                "session_id": resolved_session_id,
                "environment": "unknown",
                "mode": "",
                "started_at": _normalize_timestamp(timestamp),
                "finished_at": _normalize_timestamp(timestamp),
                "final_status": str(final_status or "FINISHED").upper(),
                "details": dict(details or {}),
                "checkpoints": [],
            }

        session["finished_at"] = _normalize_timestamp(timestamp)
        session["final_status"] = str(final_status or "FINISHED").upper()
        if details:
            merged = dict(session.get("details", {}))
            merged.update(dict(details))
            session["details"] = merged
        return dict(session)

    def get_testnet_session(self, session_id: str) -> dict[str, Any]:
        session = self._session_index.get(str(session_id or "").strip())
        return dict(session) if isinstance(session, dict) else {}

    def list_testnet_sessions(
        self,
        *,
        final_status: Optional[str] = None,
        latest: bool = False,
    ) -> list[dict[str, Any]]:
        rows = [dict(item) for item in self._sessions]
        if final_status not in (None, ""):
            status_key = str(final_status).upper()
            rows = [row for row in rows if str(row.get("final_status", "")).upper() == status_key]
        if latest:
            return [rows[-1]] if rows else []
        return rows


def _normalize_timestamp(value: Optional[Any]) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in (None, ""):
        return str(value)
    return now_iso()
