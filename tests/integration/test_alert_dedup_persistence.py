"""Integration tests for alert dedup persistence."""
from __future__ import annotations
import json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.alerts.dedup_store import DedupStore
from src.runtime_integrations.alerts.alert_replay import replay_alerts


def test_dedup_first_run_records_all():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        store = DedupStore(tmp / "store.json")
        alerts = tmp / "alerts.jsonl"
        alerts.write_text('{"dedup_key": "k1", "severity": "INFO"}\n{"dedup_key": "k2", "severity": "INFO"}\n')
        report = replay_alerts(alerts, store)
        assert report.new_alerts == 2
        assert report.suppressed_alerts == 0


def test_dedup_second_run_suppresses():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        alerts = tmp / "alerts.jsonl"
        alerts.write_text('{"dedup_key": "k1", "severity": "INFO"}\n{"dedup_key": "k1", "severity": "INFO"}\n')
        store = DedupStore(tmp / "store.json")
        report1 = replay_alerts(alerts, store)
        assert report1.new_alerts == 1
        assert report1.suppressed_alerts == 1


def test_dedup_persists_across_instances():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        store_path = tmp / "store.json"
        alerts = tmp / "alerts.jsonl"
        alerts.write_text('{"dedup_key": "k1", "severity": "INFO"}\n')
        store1 = DedupStore(store_path)
        replay_alerts(alerts, store1)
        store2 = DedupStore(store_path)
        assert store2.is_duplicate("k1")
