"""Shadow ledger — records shadow plans and outcomes. No network, no orders."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class ShadowRecord:
    """Single shadow plan record — readonly."""
    timestamp: float
    symbol: str
    timeframe: str
    priority: str  # HIGH / MEDIUM / LOW / REJECT
    signal_type: str
    plan_id: str
    valid_plan: bool
    reject_reason: str
    entry: float
    stop: float
    take_profit: float
    rr: float
    outcome: str  # WIN / LOSS / TIMEOUT / PENDING
    pnl: float
    expectancy_input: float
    data_quality_ok: bool
    safety_flags: List[str]


class ShadowLedger:
    """Append-only JSONL ledger for shadow plans. No network, no orders."""

    def __init__(self, path: str):
        self._path = path

    def append(self, record: ShadowRecord) -> None:
        """Append a record to the JSONL file."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def read_all(self) -> List[ShadowRecord]:
        """Read all records from the JSONL file."""
        if not os.path.isfile(self._path):
            return []
        records = []
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                data["safety_flags"] = data.get("safety_flags", [])
                records.append(ShadowRecord(**data))
        return records

    def summary(self) -> Dict[str, Any]:
        """Compute summary statistics from records."""
        records = self.read_all()
        valid = [r for r in records if r.valid_plan]
        high = [r for r in valid if r.priority == "HIGH"]
        medium = [r for r in valid if r.priority == "MEDIUM"]
        low = [r for r in valid if r.priority == "LOW"]

        total_pnl = sum(r.pnl for r in valid)
        wins = [r for r in valid if r.outcome == "WIN"]
        losses = [r for r in valid if r.outcome == "LOSS"]

        win_rate = len(wins) / len(valid) if valid else 0.0
        avg_win = sum(r.pnl for r in wins) / len(wins) if wins else 0.0
        avg_loss = sum(r.pnl for r in losses) / len(losses) if losses else 0.0
        profit_factor = abs(sum(r.pnl for r in wins) / sum(r.pnl for r in losses)) if losses and sum(r.pnl for r in losses) != 0 else float("inf")
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if valid else 0.0

        return {
            "total_records": len(records),
            "valid_plans": len(valid),
            "invalid_plans": len(records) - len(valid),
            "high_count": len(high),
            "medium_count": len(medium),
            "low_count": len(low),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "inf",
            "expectancy": round(expectancy, 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "high_medium_ratio": round((len(high) + len(medium)) / len(valid), 4) if valid else 0.0,
            "low_ratio": round(len(low) / len(valid), 4) if valid else 0.0,
        }

    @property
    def path(self) -> str:
        return self._path
