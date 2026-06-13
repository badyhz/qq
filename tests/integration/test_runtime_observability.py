"""Integration tests for runtime observability."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.observability.runtime_metrics import collect_metrics
from src.runtime_integrations.observability.runtime_health import evaluate_health


def test_metrics_collected():
    m = collect_metrics(ROOT / "data", ROOT / "reports")
    assert m.signal_count > 0
    assert m.alert_count > 0
    assert m.dashboard_generated is True


def test_health_ok():
    m = collect_metrics(ROOT / "data", ROOT / "reports")
    h = evaluate_health(m)
    assert h.status == "OK"
