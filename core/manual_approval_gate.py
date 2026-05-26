"""Manual Approval Gate — governance module for live adapter actions.

Every live adapter action must pass through this gate. Tokens are single-use,
TTL-expiring, and require explicit human approval before consumption.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EXPIRED = "expired"
    CONSUMED = "consumed"
    DENIED = "denied"
    REVOKED = "revoked"


@dataclass
class ApprovalRequest:
    token: str
    action: str
    adapter_id: str
    status: ApprovalStatus
    created_at: float
    expires_at: float
    approved_at: Optional[float] = None
    consumed_at: Optional[float] = None


@dataclass
class ApprovalConsumeResult:
    success: bool
    status: ApprovalStatus
    detail: str


class ManualApprovalGate:
    """Gate that requires explicit manual approval before live adapter actions.

    Tokens are single-use and expire after TTL seconds.
    """

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._requests: dict[str, ApprovalRequest] = {}
        # Index: (action, adapter_id) -> list of tokens
        self._by_action: dict[tuple[str, str], list[str]] = {}

    # -- helpers ---------------------------------------------------------------

    def _expire_if_needed(self, req: ApprovalRequest) -> None:
        """Mark a request expired if TTL has lapsed."""
        now = time.time()
        if req.status in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED):
            if now >= req.expires_at:
                req.status = ApprovalStatus.EXPIRED

    def _get(self, token: str) -> Optional[ApprovalRequest]:
        req = self._requests.get(token)
        if req is not None:
            self._expire_if_needed(req)
        return req

    # -- public API ------------------------------------------------------------

    def request_approval(
        self, action: str, adapter_id: str, ttl_seconds: int | None = None
    ) -> str:
        """Request approval. Returns a UUID token string."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        now = time.time()
        token = str(uuid.uuid4())
        req = ApprovalRequest(
            token=token,
            action=action,
            adapter_id=adapter_id,
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=now + ttl,
        )
        self._requests[token] = req
        key = (action, adapter_id)
        self._by_action.setdefault(key, []).append(token)
        return token

    def approve(self, token: str) -> bool:
        """Approve a pending request. Returns True if valid."""
        req = self._get(token)
        if req is None or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.APPROVED
        req.approved_at = time.time()
        return True

    def deny(self, token: str) -> bool:
        """Deny a pending request. Returns True if valid."""
        req = self._get(token)
        if req is None or req.status != ApprovalStatus.PENDING:
            return False
        req.status = ApprovalStatus.DENIED
        return True

    def is_approved(self, action: str, adapter_id: str) -> bool:
        """Check if an action+adapter combo has an active approved token."""
        key = (action, adapter_id)
        tokens = self._by_action.get(key, [])
        for tok in tokens:
            req = self._get(tok)
            if req is not None and req.status == ApprovalStatus.APPROVED:
                return True
        return False

    def consume(self, token: str) -> ApprovalConsumeResult:
        """Consume a single-use approval token."""
        req = self._get(token)
        if req is None:
            return ApprovalConsumeResult(
                success=False, status=ApprovalStatus.EXPIRED, detail="token not found"
            )
        if req.status == ApprovalStatus.CONSUMED:
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.CONSUMED,
                detail="token already consumed",
            )
        if req.status == ApprovalStatus.PENDING:
            return ApprovalConsumeResult(
                success=False,
                status=ApprovalStatus.PENDING,
                detail="token is still pending approval",
            )
        if req.status != ApprovalStatus.APPROVED:
            return ApprovalConsumeResult(
                success=False,
                status=req.status,
                detail=f"token is {req.status.value}",
            )
        req.status = ApprovalStatus.CONSUMED
        req.consumed_at = time.time()
        return ApprovalConsumeResult(
            success=True, status=ApprovalStatus.CONSUMED, detail="consumed"
        )

    def check_status(self, token: str) -> ApprovalStatus:
        """Get current status of a token."""
        req = self._get(token)
        if req is None:
            raise KeyError(f"token {token} not found")
        return req.status

    def revoke(self, token: str) -> bool:
        """Revoke a token (approved or pending). Returns True if valid."""
        req = self._get(token)
        if req is None:
            return False
        if req.status not in (ApprovalStatus.PENDING, ApprovalStatus.APPROVED):
            return False
        req.status = ApprovalStatus.REVOKED
        return True

    def list_pending(self) -> list[dict]:
        """List all pending approvals."""
        result = []
        for req in self._requests.values():
            self._expire_if_needed(req)
            if req.status == ApprovalStatus.PENDING:
                result.append(
                    {
                        "token": req.token,
                        "action": req.action,
                        "adapter_id": req.adapter_id,
                        "created_at": req.created_at,
                        "expires_at": req.expires_at,
                    }
                )
        return result

    def list_approved(self) -> list[dict]:
        """List all approved (unconsumed) approvals."""
        result = []
        for req in self._requests.values():
            self._expire_if_needed(req)
            if req.status == ApprovalStatus.APPROVED:
                result.append(
                    {
                        "token": req.token,
                        "action": req.action,
                        "adapter_id": req.adapter_id,
                        "approved_at": req.approved_at,
                        "expires_at": req.expires_at,
                    }
                )
        return result

    def summary(self) -> dict:
        """Gate statistics."""
        counts: dict[str, int] = {}
        for req in self._requests.values():
            self._expire_if_needed(req)
            key = req.status.value
            counts[key] = counts.get(key, 0) + 1
        return {
            "total": len(self._requests),
            "counts": counts,
            "default_ttl_seconds": self.default_ttl_seconds,
        }
