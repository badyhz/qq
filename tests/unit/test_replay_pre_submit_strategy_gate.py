from __future__ import annotations

import json
from pathlib import Path

from scripts.replay_pre_submit_strategy_gate import replay_pre_submit_strategy_gate


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_replay_summary_counts_deterministic(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    logs = tmp_path / "logs"
    out_dir = tmp_path / "out"

    (reports / "system_health").mkdir(parents=True, exist_ok=True)
    (reports / "system_health" / "trading_system_health_dashboard.json").write_text(
        json.dumps({"final_verdict": "PASS", "next_action": ""}, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_csv(
        reports / "strategy_promotion" / "strategy_promotion_decisions.csv",
        [
            {"strategy_key": "BTCUSDT_LONG_5m", "symbol": "BTCUSDT", "side": "LONG", "timeframe": "5m", "promotion_decision": "PROMOTE_TO_OBSERVATION", "required_next_samples": "1"},
            {"strategy_key": "ETHUSDT_SHORT_5m", "symbol": "ETHUSDT", "side": "SHORT", "timeframe": "5m", "promotion_decision": "REJECT_STRATEGY", "required_next_samples": "5"},
        ],
        ["strategy_key", "symbol", "side", "timeframe", "promotion_decision", "required_next_samples"],
    )
    _write_csv(
        reports / "symbol_side_recommendations" / "symbol_side_recommendations.csv",
        [
            {"strategy_key": "BTCUSDT_LONG_5m", "symbol": "BTCUSDT", "side": "LONG", "timeframe": "5m", "recommendation": "PROMOTE"},
            {"strategy_key": "ETHUSDT_SHORT_5m", "symbol": "ETHUSDT", "side": "SHORT", "timeframe": "5m", "recommendation": "BLACKLIST"},
        ],
        ["strategy_key", "symbol", "side", "timeframe", "recommendation"],
    )
    _write_csv(
        reports / "strategy_candidate_score" / "strategy_candidate_score.csv",
        [
            {"strategy_key": "BTCUSDT_LONG_5m", "symbol": "BTCUSDT", "side": "LONG", "timeframe": "5m", "sample_confidence_level": "MEDIUM"},
            {"strategy_key": "ETHUSDT_SHORT_5m", "symbol": "ETHUSDT", "side": "SHORT", "timeframe": "5m", "sample_confidence_level": "MEDIUM"},
        ],
        ["strategy_key", "symbol", "side", "timeframe", "sample_confidence_level"],
    )
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "multi_day_performance_report.json").write_text(json.dumps({"final_verdict": "PASS"}), encoding="utf-8")

    candidates_jsonl = tmp_path / "candidates.jsonl"
    _write_jsonl(
        candidates_jsonl,
        [
            {"candidate_id": "cand_a", "symbol": "BTCUSDT", "side": "BUY", "timeframe": "5m", "strategy_key": "BTCUSDT_LONG_5m", "status": "APPROVED"},
            {"candidate_id": "cand_b", "symbol": "ETHUSDT", "side": "SELL", "timeframe": "5m", "strategy_key": "ETHUSDT_SHORT_5m", "status": "PENDING"},
        ],
    )

    summary = replay_pre_submit_strategy_gate(
        candidates_jsonl=str(candidates_jsonl),
        reports_dir=str(reports),
        logs_dir=str(logs),
        output_dir=str(out_dir),
    )

    assert summary["ok"] is True
    assert summary["candidate_count"] == 2
    assert summary["would_allow_submit_count"] == 1
    assert summary["would_block_count"] == 1
    assert Path(summary["csv_path"]).exists()
    assert Path(summary["summary_json"]).exists()
    assert Path(summary["summary_md"]).exists()
