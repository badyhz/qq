"""Scheduled E2E simulator. Simulates scheduled runs without real timers."""
from __future__ import annotations
import json, pathlib, tempfile, sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@dataclass(frozen=True)
class ScheduledRun:
    run_index: int
    scheduled_time: str
    actual_time: str
    status: str  # COMPLETED, SKIPPED_LOCK, FAILED
    duration_ms: float
    def to_dict(self) -> dict:
        return {"run_index": self.run_index, "scheduled_time": self.scheduled_time, "actual_time": self.actual_time, "status": self.status, "duration_ms": self.duration_ms}

def simulate_scheduled_runs(num_runs: int, interval_minutes: int = 60) -> list[ScheduledRun]:
    """Simulate scheduled E2E runs."""
    from src.runtime_integrations.e2e.system_dry_run_e2e import run_e2e
    runs = []
    base_time = datetime.now(timezone.utc)
    for i in range(num_runs):
        scheduled = base_time + timedelta(minutes=i * interval_minutes)
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = pathlib.Path(tmpdir)
            data_dir = tmp / "data"
            reports_dir = tmp / "reports"
            data_dir.mkdir(); reports_dir.mkdir()
            x_dir = data_dir / "x_exports"; x_dir.mkdir(parents=True)
            (x_dir / "test.jsonl").write_text('{"tickers": ["BTC"], "timestamp": "2026-06-01", "source_file": "sched.md"}\n')
            start = datetime.now(timezone.utc)
            try:
                result = run_e2e(data_dir, reports_dir)
                end = datetime.now(timezone.utc)
                duration = (end - start).total_seconds() * 1000
                status = "COMPLETED" if result.get("status") == "SYSTEM_DRY_RUN_E2E_PASS" else "FAILED"
            except Exception:
                end = datetime.now(timezone.utc)
                duration = (end - start).total_seconds() * 1000
                status = "FAILED"
            runs.append(ScheduledRun(i, scheduled.isoformat(), datetime.now(timezone.utc).isoformat(), status, round(duration, 1)))
    return runs

def write_runs(runs: list[ScheduledRun], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r.to_dict()) for r in runs) + ("\n" if runs else ""), encoding="utf-8")
