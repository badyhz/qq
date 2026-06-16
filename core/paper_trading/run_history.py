"""Run history — JSONL append, read, compare, trend analysis. No network."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import List, Optional, Dict, Any


DEFAULT_HISTORY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "reports", "paper_trading_run_history.jsonl"
)


@dataclass(frozen=True)
class RunRecord:
    timestamp: str
    strategy_name: str
    status: str
    fixtures_run: int
    fixtures_failed: int
    total_signals: int
    total_plans: int
    total_rejected: int
    total_trades: int
    total_pnl: float
    win_rate: float
    score: float
    rating: str
    alerts_written: int


@dataclass(frozen=True)
class TrendDelta:
    score: float
    pnl: float
    win_rate: float
    trades: int
    improved: bool


def record_from_result(result) -> RunRecord:
    """Convert a RuntimeResult to a RunRecord."""
    return RunRecord(
        timestamp=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        strategy_name=result.strategy_name,
        status=result.status,
        fixtures_run=result.fixtures_run,
        fixtures_failed=result.fixtures_failed,
        total_signals=result.total_signals,
        total_plans=result.total_plans,
        total_rejected=result.total_rejected,
        total_trades=result.total_trades,
        total_pnl=round(result.total_pnl, 2),
        win_rate=round(result.win_rate, 4),
        score=round(result.score, 2),
        rating=result.rating,
        alerts_written=result.alerts_written,
    )


def append_record(record: RunRecord, path: Optional[str] = None) -> str:
    """Append a RunRecord as one JSON line. Returns the path written."""
    path = path or DEFAULT_HISTORY_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(asdict(record)) + "\n")
    return path


def read_history(path: Optional[str] = None, limit: int = 0) -> List[RunRecord]:
    """Read run history. limit=0 means all."""
    path = path or DEFAULT_HISTORY_PATH
    if not os.path.isfile(path):
        return []
    records: List[RunRecord] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(RunRecord(**data))
            except (json.JSONDecodeError, TypeError):
                continue
    if limit > 0:
        records = records[-limit:]
    return records


def filter_by_date(records: List[RunRecord], target_date: str) -> List[RunRecord]:
    """Filter records by date prefix (YYYY-MM-DD)."""
    return [r for r in records if r.timestamp.startswith(target_date)]


def compare_last_two(records: List[RunRecord]) -> Optional[TrendDelta]:
    """Compare the last two records and return the delta."""
    if len(records) < 2:
        return None
    prev, curr = records[-2], records[-1]
    score_delta = round(curr.score - prev.score, 2)
    pnl_delta = round(curr.total_pnl - prev.total_pnl, 2)
    wr_delta = round(curr.win_rate - prev.win_rate, 4)
    trades_delta = curr.total_trades - prev.total_trades
    improved = score_delta >= 0 and pnl_delta >= 0
    return TrendDelta(
        score=score_delta,
        pnl=pnl_delta,
        win_rate=wr_delta,
        trades=trades_delta,
        improved=improved,
    )


def compute_trend(records: List[RunRecord], window: int = 5) -> Dict[str, Any]:
    """Compute trend stats over the last `window` records."""
    if not records:
        return {"count": 0, "avg_score": 0, "avg_pnl": 0, "avg_win_rate": 0,
                "score_trend": "flat", "pnl_trend": "flat"}
    recent = records[-window:]
    avg_score = sum(r.score for r in recent) / len(recent)
    avg_pnl = sum(r.total_pnl for r in recent) / len(recent)
    avg_wr = sum(r.win_rate for r in recent) / len(recent)

    score_trend = _trend_direction([r.score for r in recent])
    pnl_trend = _trend_direction([r.total_pnl for r in recent])

    return {
        "count": len(recent),
        "avg_score": round(avg_score, 2),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win_rate": round(avg_wr, 4),
        "score_trend": score_trend,
        "pnl_trend": pnl_trend,
    }


def _trend_direction(values: List[float]) -> str:
    """Simple trend: rising / falling / flat."""
    if len(values) < 2:
        return "flat"
    first_half = sum(values[: len(values) // 2]) / max(len(values) // 2, 1)
    second_half = sum(values[len(values) // 2 :]) / max(len(values) - len(values) // 2, 1)
    diff = second_half - first_half
    if diff > 0.01:
        return "rising"
    elif diff < -0.01:
        return "falling"
    return "flat"
