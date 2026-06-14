"""Unit test: paper ops alert payload."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_ops.models import DailyOpsBundle, new_id, utc_now_iso
from src.paper_trading_ops.ops_alert_payload import generate_alert_payload


def _make_bundle() -> DailyOpsBundle:
    return DailyOpsBundle(
        bundle_id=new_id("DOB"), created_at=utc_now_iso(),
        date="2026-06-15", freshness_status="FRESH",
        paper_state_status="PASS", strategy_sample_status="PROMISING",
        dashboard_grade="B", critical_alerts=[], warnings=["minor"],
        recommended_actions=["monitor"], operator_checklist=["check"],
        final_verdict="DAILY_PAPER_OPS_BUNDLE_READY|PAPER_TRADING_OPS_WARNING|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )


def test_alert_dry_run() -> None:
    payload = generate_alert_payload(_make_bundle())
    assert payload.dry_run_only is True


def test_alert_verdict_format() -> None:
    payload = generate_alert_payload(_make_bundle())
    assert "DRY_RUN_ONLY=TRUE" in payload.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in payload.final_verdict


def test_alert_title() -> None:
    payload = generate_alert_payload(_make_bundle())
    assert "[DRY-RUN]" in payload.title


def test_alert_to_dict() -> None:
    payload = generate_alert_payload(_make_bundle())
    d = payload.to_dict()
    assert "payload_id" in d
    assert d["dry_run_only"] is True


def test_alert_fields_match_bundle() -> None:
    bundle = _make_bundle()
    payload = generate_alert_payload(bundle)
    assert payload.date == bundle.date
    assert payload.freshness_status == bundle.freshness_status
    assert payload.dashboard_grade == bundle.dashboard_grade


def main() -> None:
    test_alert_dry_run()
    test_alert_verdict_format()
    test_alert_title()
    test_alert_to_dict()
    test_alert_fields_match_bundle()
    print("test_paper_ops_alert_payload: ALL PASS")


if __name__ == "__main__":
    main()
