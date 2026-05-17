from __future__ import annotations

from pathlib import Path

from scripts import run_public_kline_backfill as backfill


def _write_plan_csv(path: Path) -> None:
    path.write_text(
        "symbol,timeframe,required_bars,cache_status\nBTCUSDT,5m,120,MISSING\n",
        encoding="utf-8",
    )


def test_validate_backfill_execution_mode_defaults_to_planning() -> None:
    mode = backfill.validate_backfill_execution_mode(execute_fetch=False, dry_run=False, write_cache=False)
    assert mode["dry_run"] is True
    assert mode["network_enabled"] is False


def test_validate_backfill_execution_mode_allows_network_only_with_execute_flag() -> None:
    mode = backfill.validate_backfill_execution_mode(execute_fetch=True, dry_run=False, write_cache=False)
    assert mode["dry_run"] is False
    assert mode["network_enabled"] is True


def test_run_public_kline_backfill_execute_flag_required_for_fetch(tmp_path: Path, monkeypatch) -> None:
    plan_csv = tmp_path / "plan.csv"
    _write_plan_csv(plan_csv)

    def _fail_fetch(**_: object) -> dict[str, object]:
        raise AssertionError("network fetch should not run when execute_fetch is false")

    monkeypatch.setattr(backfill, "_fetch_public_klines", _fail_fetch)

    summary = backfill.run_public_kline_backfill(
        plan_csv=str(plan_csv),
        cache_dir=str(tmp_path / "cache"),
        output_dir=str(tmp_path / "out"),
        max_symbols=1,
        max_bars=300,
        market="futures",
        dry_run=False,
        write_cache=True,
        public_only=True,
        execute_fetch=False,
    )

    assert summary["network_enabled"] is False
    assert summary["dry_run"] is True
    assert int(summary["dry_run_only_count"]) == 1
    assert int(summary["fetched_bars_total"]) == 0
