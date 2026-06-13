#!/usr/bin/env python3
"""T68001 — Alert Dedup Replay."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.alerts.dedup_store import DedupStore
from src.runtime_integrations.alerts.alert_replay import replay_alerts, write_report

def main():
    alerts_path = ROOT / "data" / "runtime" / "alerts" / "alerts.jsonl"
    store_path = ROOT / "data" / "runtime" / "alerts" / "dedup_store.json"
    store = DedupStore(store_path)
    report = replay_alerts(alerts_path, store)
    write_report(report, ROOT / "data" / "runtime" / "alerts" / "dedup_replay_report.json")
    print(f"Dedup: loaded={report.alerts_loaded}, new={report.new_alerts}, suppressed={report.suppressed_alerts}")

if __name__ == "__main__":
    main()
