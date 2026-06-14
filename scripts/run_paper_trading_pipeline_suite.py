"""Suite runner: paper trading pipeline."""
from __future__ import annotations
import importlib, json, pathlib, sys, uuid
from datetime import datetime, timezone
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

RUNNERS = (
    "scripts.run_paper_trading_log_source_check",
    "scripts.run_paper_trading_signal_dedup",
    "scripts.run_paper_trade_plan_batch",
    "scripts.run_paper_position_store_update",
    "scripts.run_paper_position_replay_update",
    "scripts.run_daily_paper_trading_review",
    "scripts.run_feishu_paper_review_payload_dry_run",
    "scripts.run_paper_trading_pipeline_safety_regression",
)
OUT = pathlib.Path("reports/paper_trading/suite_result.json")


def main() -> None:
    results = []
    for mod_name in RUNNERS:
        try:
            mod = importlib.import_module(mod_name)
            mod.main()
            results.append({"runner": mod_name, "status": "PASS"})
        except Exception as e:
            results.append({"runner": mod_name, "status": "FAIL", "error": str(e)})
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    suite = {
        "suite_id": f"PTS_{uuid.uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runners": results, "passed": passed, "total": total,
        "final_verdict": f"PAPER_TRADING_PIPELINE_SUITE_{'PASS' if passed == total else 'FAIL'}|{passed}/{total}|REAL_ORDER_SUBMIT_NOT_ALLOWED|REAL_TRADING_NOT_ALLOWED",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(suite, indent=2), encoding="utf-8")
    print(f"suite: {passed}/{total} passed | verdict={suite['final_verdict']}")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
