"""Single-call evidence recorder.

Pure data recorder for one future real adapter call.
No network. No secrets. No raw API keys. No full payloads.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class CallRecord:
    record_id: str
    adapter_id: str
    request_id: str
    started_at: float
    ended_at: float | None = None
    duration_ms: float | None = None
    capability_used: str = ""
    approval_token_hash: str = ""
    budget_before_usd: float = 0.0
    budget_after_usd: float | None = None
    response_status: str | None = None
    response_summary: str | None = None

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "adapter_id": self.adapter_id,
            "request_id": self.request_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "capability_used": self.capability_used,
            "approval_token_hash": self.approval_token_hash,
            "budget_before_usd": self.budget_before_usd,
            "budget_after_usd": self.budget_after_usd,
            "response_status": self.response_status,
            "response_summary": self.response_summary,
        }


_RESPONSE_SUMMARY_MAX_LEN = 200


class SingleCallRecorder:
    """Records evidence of a single adapter call. No I/O."""

    def __init__(self) -> None:
        self._records: dict[str, CallRecord] = {}

    def _hash_token(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def _truncate_summary(self, summary: str) -> str:
        if len(summary) <= _RESPONSE_SUMMARY_MAX_LEN:
            return summary
        return summary[:_RESPONSE_SUMMARY_MAX_LEN]

    def start_record(
        self,
        adapter_id: str,
        request_id: str,
        capability_used: str,
        approval_token: str,
        budget_before_usd: float,
    ) -> str:
        record_id = str(uuid.uuid4())
        record = CallRecord(
            record_id=record_id,
            adapter_id=adapter_id,
            request_id=request_id,
            started_at=time.time(),
            capability_used=capability_used,
            approval_token_hash=self._hash_token(approval_token),
            budget_before_usd=budget_before_usd,
        )
        self._records[record_id] = record
        return record_id

    def end_record(
        self,
        record_id: str,
        response_status: str,
        response_summary: str,
        budget_after_usd: float,
    ) -> None:
        record = self._records.get(record_id)
        if record is None:
            raise KeyError(f"unknown record_id: {record_id}")
        now = time.time()
        record.ended_at = now
        record.duration_ms = (now - record.started_at) * 1000.0
        record.response_status = response_status
        record.response_summary = self._truncate_summary(response_summary)
        record.budget_after_usd = budget_after_usd

    def get_record(self, record_id: str) -> CallRecord | None:
        return self._records.get(record_id)

    def list_records(self) -> list[CallRecord]:
        return list(self._records.values())

    def summary(self) -> dict:
        records = list(self._records.values())
        by_adapter: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for r in records:
            by_adapter[r.adapter_id] = by_adapter.get(r.adapter_id, 0) + 1
            if r.response_status is not None:
                by_status[r.response_status] = by_status.get(r.response_status, 0) + 1
        return {
            "total_calls": len(records),
            "by_adapter": by_adapter,
            "by_status": by_status,
        }
