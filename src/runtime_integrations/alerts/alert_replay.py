"""Alert replay. Replays alerts through dedup store."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone

from src.runtime_integrations.alerts.dedup_store import DedupStore


@dataclass(frozen=True)
class ReplayReport:
    run_id: str
    alerts_loaded: int
    new_alerts: int
    suppressed_alerts: int
    dedup_store_size: int
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "alerts_loaded": self.alerts_loaded,
            "new_alerts": self.new_alerts,
            "suppressed_alerts": self.suppressed_alerts,
            "dedup_store_size": self.dedup_store_size,
            "timestamp": self.timestamp,
        }


def replay_alerts(alerts_path: pathlib.Path, store: DedupStore) -> ReplayReport:
    """Replay alerts through dedup store."""
    now = datetime.now(timezone.utc).isoformat()
    new_count = 0
    suppress_count = 0
    loaded = 0

    if alerts_path.exists():
        for line in alerts_path.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            try:
                alert = json.loads(line)
            except json.JSONDecodeError:
                continue
            loaded += 1
            key = alert.get("dedup_key", "")
            severity = alert.get("severity", "INFO")
            if store.record(key, severity):
                new_count += 1
            else:
                suppress_count += 1

    store.save()
    return ReplayReport(
        run_id=f"replay_{now.replace(':', '').replace('-', '')[:20]}",
        alerts_loaded=loaded,
        new_alerts=new_count,
        suppressed_alerts=suppress_count,
        dedup_store_size=store.total_unique(),
        timestamp=now,
    )


def write_report(report: ReplayReport, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
