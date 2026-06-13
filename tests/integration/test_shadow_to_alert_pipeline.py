"""Integration test for shadow-to-alert pipeline."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.runtime_integrations.shadow.shadow_runtime import generate_signals_from_watchlist, build_scorecard, write_signals
from src.runtime_integrations.alerts.alert_runtime import load_alerts_from_signals, deduplicate_alerts, write_alerts


def test_shadow_signals_flow_to_alerts():
    """Shadow signals are consumed by alert runtime."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        signals_path = tmp / "signals.jsonl"
        alerts_path = tmp / "alerts.jsonl"

        # Generate signals
        watchlist = [
            {"ticker": "BTC", "score": 0.8, "source": "test.md"},
            {"ticker": "ETH", "score": 0.6, "source": "test.md"},
        ]
        signals = generate_signals_from_watchlist(watchlist, "test_run")
        write_signals(signals, signals_path)

        # Load as alerts
        alerts = load_alerts_from_signals(signals_path)
        assert len(alerts) > 0
        assert alerts[0].source == "shadow"
        assert alerts[0].dry_run is True

        # Verify ticker propagation
        tickers = {a.ticker for a in alerts}
        assert "BTC" in tickers
        assert "ETH" in tickers


def test_alert_deduplication():
    """Duplicate alerts from same source are deduplicated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        signals_path = tmp / "signals.jsonl"

        # Create signals with same ticker
        signals = [
            {"signal_id": "s1", "ticker": "BTC", "direction": "BUY", "confidence": 0.8, "signal_type": "test"},
            {"signal_id": "s2", "ticker": "BTC", "direction": "BUY", "confidence": 0.9, "signal_type": "test"},
        ]
        write_signals_path = tmp / "write_signals.jsonl"
        write_signals_path.write_text(
            "\n".join(json.dumps(s) for s in signals),
            encoding="utf-8",
        )

        alerts = load_alerts_from_signals(write_signals_path)
        deduped = deduplicate_alerts(alerts)
        # Same ticker+source+type = same dedup_key, so deduped to 1
        assert len(deduped) == 1
