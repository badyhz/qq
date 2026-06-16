"""Review queue — local JSONL queue for operator review. No network, no orders."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any


class OperatorStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    WATCHLIST = "WATCHLIST"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    PAPER_APPROVED = "PAPER_APPROVED"


VALID_STATUSES = {s.value for s in OperatorStatus}

DEFAULT_QUEUE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "reports", "paper_trading_review_queue.jsonl"
)


@dataclass(frozen=True)
class ReviewCandidate:
    review_id: str
    timestamp: str
    symbol: str
    strategy_name: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    score: float
    rating: str
    risk_summary: str
    operator_status: str
    decision_reason: str
    source_run_id: str
    safety_flags: List[str]


def create_candidate(
    symbol: str,
    strategy_name: str,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    score: float,
    rating: str,
    risk_summary: str = "",
    source_run_id: str = "",
) -> ReviewCandidate:
    """Create a new review candidate with generated ID and timestamp."""
    return ReviewCandidate(
        review_id=uuid.uuid4().hex[:12],
        timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        symbol=symbol,
        strategy_name=strategy_name,
        side=side,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        score=score,
        rating=rating,
        risk_summary=risk_summary,
        operator_status=OperatorStatus.PENDING_REVIEW.value,
        decision_reason="",
        source_run_id=source_run_id,
        safety_flags=["NO_REAL_ORDER", "PAPER_ONLY", "HUMAN_REVIEW_REQUIRED"],
    )


def append_candidate(candidate: ReviewCandidate, path: Optional[str] = None) -> str:
    """Append a candidate to the JSONL queue. Returns path written."""
    path = path or DEFAULT_QUEUE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(asdict(candidate)) + "\n")
    return path


def read_queue(path: Optional[str] = None, status: Optional[str] = None) -> List[ReviewCandidate]:
    """Read queue entries, optionally filtered by status."""
    path = path or DEFAULT_QUEUE_PATH
    if not os.path.isfile(path):
        return []
    candidates: List[ReviewCandidate] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                c = ReviewCandidate(**data)
                if status is None or c.operator_status == status:
                    candidates.append(c)
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
    return candidates


def read_pending(path: Optional[str] = None) -> List[ReviewCandidate]:
    """Read all PENDING_REVIEW entries."""
    return read_queue(path, OperatorStatus.PENDING_REVIEW.value)


def update_status(
    review_id: str,
    new_status: str,
    reason: str = "",
    path: Optional[str] = None,
) -> bool:
    """Update a candidate's status. Returns True if found and updated."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}")

    path = path or DEFAULT_QUEUE_PATH
    if not os.path.isfile(path):
        return False

    lines: List[str] = []
    found = False
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                lines.append(line)
                continue
            try:
                data = json.loads(stripped)
                if data.get("review_id") == review_id:
                    data["operator_status"] = new_status
                    data["decision_reason"] = reason
                    lines.append(json.dumps(data) + "\n")
                    found = True
                else:
                    lines.append(line)
            except (json.JSONDecodeError, TypeError):
                lines.append(line)

    if found:
        with open(path, "w") as f:
            f.writelines(lines)
    return found


def mark_watchlist(review_id: str, reason: str = "", path: Optional[str] = None) -> bool:
    return update_status(review_id, OperatorStatus.WATCHLIST.value, reason, path)


def mark_rejected(review_id: str, reason: str = "", path: Optional[str] = None) -> bool:
    return update_status(review_id, OperatorStatus.REJECTED.value, reason, path)


def mark_paper_approved(review_id: str, reason: str = "", path: Optional[str] = None) -> bool:
    """Mark as PAPER_APPROVED. This does NOT create real orders."""
    return update_status(review_id, OperatorStatus.PAPER_APPROVED.value, reason, path)


def expire_old(path: Optional[str] = None, max_age_hours: int = 24) -> int:
    """Expire PENDING_REVIEW entries older than max_age_hours. Returns count expired."""
    path = path or DEFAULT_QUEUE_PATH
    if not os.path.isfile(path):
        return 0

    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    cutoff_str = cutoff.isoformat(timespec="seconds") + "Z"

    lines: List[str] = []
    expired = 0
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                lines.append(line)
                continue
            try:
                data = json.loads(stripped)
                if (data.get("operator_status") == OperatorStatus.PENDING_REVIEW.value
                        and data.get("timestamp", "") < cutoff_str):
                    data["operator_status"] = OperatorStatus.EXPIRED.value
                    data["decision_reason"] = "auto-expired"
                    lines.append(json.dumps(data) + "\n")
                    expired += 1
                else:
                    lines.append(line)
            except (json.JSONDecodeError, TypeError):
                lines.append(line)

    if expired > 0:
        with open(path, "w") as f:
            f.writelines(lines)
    return expired


def queue_summary(path: Optional[str] = None) -> Dict[str, int]:
    """Count entries by status."""
    candidates = read_queue(path)
    summary: Dict[str, int] = {s.value: 0 for s in OperatorStatus}
    for c in candidates:
        if c.operator_status in summary:
            summary[c.operator_status] += 1
    summary["total"] = len(candidates)
    return summary
