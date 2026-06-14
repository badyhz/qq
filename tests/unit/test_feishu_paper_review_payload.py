"""Unit test: Feishu paper review payload."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from src.paper_trading_pipeline.feishu_paper_review_payload import generate_feishu_payload
from src.paper_trading_pipeline.models import DailyPaperReview


def _make_review() -> DailyPaperReview:
    return DailyPaperReview(
        review_id="DPR1", created_at="", date="2026-06-14",
        raw_signals=3, deduped_signals=3, trade_plans_created=3,
        paper_positions_total=3, paper_open_count=2, paper_closed_count=1,
        tp1_count=1, tp2_count=0, tp3_count=0, stop_count=1, time_stop_count=0,
        win_rate_placeholder=50.0, expectancy_r_placeholder=0.5,
        top_symbols=["BTCUSDT"], risk_notes=[], data_quality_notes=[],
        next_actions=["Continue monitoring"],
        final_verdict="TEST")


def test_payload_dry_run() -> None:
    payload = generate_feishu_payload(_make_review())
    assert payload.dry_run_only is True


def test_payload_fields() -> None:
    payload = generate_feishu_payload(_make_review())
    assert payload.date == "2026-06-14"
    assert payload.raw_signals == 3
    assert "DRY-RUN" in payload.title


def test_payload_verdict() -> None:
    payload = generate_feishu_payload(_make_review())
    assert "DRY_RUN_READY" in payload.final_verdict
    assert "REAL_ORDER_SUBMIT_NOT_ALLOWED" in payload.final_verdict


def test_payload_no_credentials() -> None:
    payload = generate_feishu_payload(_make_review())
    d = payload.to_dict()
    for v in d.values():
        if isinstance(v, str):
            assert "FEISHU_WEBHOOK" not in v.upper()
            assert "SECRET" not in v.upper()


def main() -> None:
    test_payload_dry_run()
    test_payload_fields()
    test_payload_verdict()
    test_payload_no_credentials()
    print("test_feishu_paper_review_payload: ALL PASS")


if __name__ == "__main__":
    main()
