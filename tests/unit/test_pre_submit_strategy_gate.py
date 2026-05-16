from __future__ import annotations

import json
from pathlib import Path

from scripts.pre_submit_strategy_gate import pre_submit_strategy_gate


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _bootstrap_reports(tmp_path: Path, *, health_verdict: str, next_action: str, recommendation: str, promotion_decision: str, sample_confidence: str) -> tuple[Path, Path]:
    reports = tmp_path / "reports"
    logs = tmp_path / "logs"
    (reports / "system_health").mkdir(parents=True, exist_ok=True)
    (reports / "strategy_promotion").mkdir(parents=True, exist_ok=True)
    (reports / "symbol_side_recommendations").mkdir(parents=True, exist_ok=True)
    (reports / "strategy_candidate_score").mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)

    (reports / "system_health" / "trading_system_health_dashboard.json").write_text(
        json.dumps({"final_verdict": health_verdict, "next_action": next_action}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_csv(
        reports / "strategy_promotion" / "strategy_promotion_decisions.csv",
        [
            {
                "strategy_key": "BTCUSDT_LONG_5m",
                "symbol": "BTCUSDT",
                "side": "LONG",
                "timeframe": "5m",
                "promotion_decision": promotion_decision,
                "required_next_samples": "3",
            }
        ],
        ["strategy_key", "symbol", "side", "timeframe", "promotion_decision", "required_next_samples"],
    )
    _write_csv(
        reports / "symbol_side_recommendations" / "symbol_side_recommendations.csv",
        [
            {
                "strategy_key": "BTCUSDT_LONG_5m",
                "symbol": "BTCUSDT",
                "side": "LONG",
                "timeframe": "5m",
                "recommendation": recommendation,
            }
        ],
        ["strategy_key", "symbol", "side", "timeframe", "recommendation"],
    )
    _write_csv(
        reports / "strategy_candidate_score" / "strategy_candidate_score.csv",
        [
            {
                "strategy_key": "BTCUSDT_LONG_5m",
                "symbol": "BTCUSDT",
                "side": "LONG",
                "timeframe": "5m",
                "sample_confidence_level": sample_confidence,
            }
        ],
        ["strategy_key", "symbol", "side", "timeframe", "sample_confidence_level"],
    )
    (logs / "multi_day_performance_report.json").write_text(
        json.dumps({"final_verdict": "PASS"}, ensure_ascii=False),
        encoding="utf-8",
    )
    return reports, logs


def test_gate_blocks_when_system_health_fail(tmp_path: Path) -> None:
    reports, logs = _bootstrap_reports(
        tmp_path,
        health_verdict="FAIL",
        next_action="",
        recommendation="PROMOTE",
        promotion_decision="PROMOTE_TO_OBSERVATION",
        sample_confidence="SUFFICIENT",
    )
    result = pre_submit_strategy_gate(
        candidate_id="cand_1",
        symbol="BTCUSDT",
        side="BUY",
        timeframe="5m",
        strategy_key="BTCUSDT_LONG_5m",
        reports_dir=str(reports),
        logs_dir=str(logs),
    )
    assert result["submit_allowed"] is False
    assert result["dry_run_allowed"] is True
    assert result["gate_decision"] == "BLOCK_SYSTEM_HEALTH"
    assert "system_health_fail" in result["reason"]


def test_gate_allows_submit_when_all_signals_good(tmp_path: Path) -> None:
    reports, logs = _bootstrap_reports(
        tmp_path,
        health_verdict="PASS",
        next_action="",
        recommendation="PROMOTE",
        promotion_decision="PROMOTE_TO_OBSERVATION",
        sample_confidence="MEDIUM",
    )
    result = pre_submit_strategy_gate(
        candidate_id="cand_2",
        symbol="BTCUSDT",
        side="BUY",
        timeframe="5m",
        strategy_key="BTCUSDT_LONG_5m",
        reports_dir=str(reports),
        logs_dir=str(logs),
    )
    assert result["gate_decision"] == "ALLOW_TESTNET_AFTER_RESET"
    assert result["submit_allowed"] is True
    assert result["dry_run_allowed"] is True
    assert "meets_gate_requirements" in result["reason"]


def test_gate_daily_limit_forces_dry_run_only(tmp_path: Path) -> None:
    reports, logs = _bootstrap_reports(
        tmp_path,
        health_verdict="PASS",
        next_action="DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED",
        recommendation="PROMOTE",
        promotion_decision="PROMOTE_TO_OBSERVATION",
        sample_confidence="MEDIUM",
    )
    result = pre_submit_strategy_gate(
        candidate_id="cand_3",
        symbol="BTCUSDT",
        side="BUY",
        timeframe="5m",
        strategy_key="BTCUSDT_LONG_5m",
        reports_dir=str(reports),
        logs_dir=str(logs),
    )
    assert result["submit_allowed"] is False
    assert result["dry_run_allowed"] is True
    assert result["gate_decision"] in {"ALLOW_DRY_RUN", "BLOCK_LOW_SAMPLE"}
    assert "max_daily_submits_reached" in result["reason"]
