from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ReviewStatus(Enum):
    PROPOSED = "proposed"
    REVIEWING = "reviewing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONFLICT = "conflict"


TERMINAL_STATUSES = frozenset({ReviewStatus.ACCEPTED, ReviewStatus.REJECTED})


@dataclass
class MergeRequest:
    id: str
    component_path: str
    proposing_task: str
    proposing_agent: str
    status: ReviewStatus
    canonical_hash: str
    candidate_hash: str
    review_notes: str
    created_at: str


class MergeReviewPipeline:
    def __init__(self) -> None:
        self._requests: dict[str, MergeRequest] = {}
        self._canonical_hashes: dict[str, str] = {}
        self._counter: int = 0

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def propose(
        self,
        component_path: str,
        proposing_task: str,
        candidate_hash: str,
        proposing_agent: str = "",
    ) -> MergeRequest:
        """Create a merge request. Auto-detects conflict if candidate != canonical."""
        self._counter += 1
        mr_id = f"MR-{self._counter:04d}"
        canonical_hash = self._canonical_hashes.get(component_path, "")
        if canonical_hash and canonical_hash != candidate_hash:
            status = ReviewStatus.CONFLICT
        else:
            status = ReviewStatus.PROPOSED
        now = datetime.now(timezone.utc).isoformat()
        mr = MergeRequest(
            id=mr_id,
            component_path=component_path,
            proposing_task=proposing_task,
            proposing_agent=proposing_agent,
            status=status,
            canonical_hash=canonical_hash,
            candidate_hash=candidate_hash,
            review_notes="",
            created_at=now,
        )
        self._requests[mr_id] = mr
        return mr

    def review(self, mr_id: str, reviewer_task: str, notes: str = "") -> MergeRequest:
        """Move to REVIEWING status."""
        mr = self._get_or_raise(mr_id)
        mr.status = ReviewStatus.REVIEWING
        if notes:
            mr.review_notes = notes
        return mr

    def accept(self, mr_id: str, reviewer_task: str) -> MergeRequest:
        """Accept the merge. Updates canonical hash."""
        mr = self._get_or_raise(mr_id)
        mr.status = ReviewStatus.ACCEPTED
        self._canonical_hashes[mr.component_path] = mr.candidate_hash
        return mr

    def reject(self, mr_id: str, reviewer_task: str, reason: str = "") -> MergeRequest:
        """Reject the merge."""
        mr = self._get_or_raise(mr_id)
        mr.status = ReviewStatus.REJECTED
        if reason:
            mr.review_notes = reason
        return mr

    def detect_conflicts(self, component_path: str) -> list[MergeRequest]:
        """Find all open MRs for a component that might conflict."""
        return [
            mr
            for mr in self._requests.values()
            if mr.component_path == component_path and mr.status not in TERMINAL_STATUSES
        ]

    def get(self, mr_id: str) -> Optional[MergeRequest]:
        """Get MR by ID."""
        return self._requests.get(mr_id)

    def list_open(self) -> list[MergeRequest]:
        """List all non-terminal MRs."""
        return [mr for mr in self._requests.values() if mr.status not in TERMINAL_STATUSES]

    def set_canonical(self, component_path: str, content_hash: str) -> None:
        """Set canonical hash for a component."""
        self._canonical_hashes[component_path] = content_hash

    def summary(self) -> dict:
        """Pipeline stats."""
        counts: dict[str, int] = {}
        for mr in self._requests.values():
            key = mr.status.value
            counts[key] = counts.get(key, 0) + 1
        return {
            "total_mrs": len(self._requests),
            "open_mrs": len(self.list_open()),
            "by_status": counts,
            "tracked_components": len(self._canonical_hashes),
        }

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _get_or_raise(self, mr_id: str) -> MergeRequest:
        mr = self._requests.get(mr_id)
        if mr is None:
            raise KeyError(f"Unknown MR: {mr_id}")
        return mr
