"""Suite runner: MACD rebound external integration."""
from __future__ import annotations
import importlib, json, pathlib, sys, uuid
from datetime import datetime, timezone
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

RUNNERS = (
    "scripts.run_macd_rebound_external_health_check",
    "scripts.run_macd_rebound_log_ingest",
    "scripts.run_macd_rebound_daily_report",
    "scripts.run_macd_rebound_deployment_audit",
    "scripts.run_macd_rebound_dry_run_plan",
    "scripts.run_macd_rebound_integration_safety_regression",
)
OUT = pathlib.Path("reports/macd_rebound/suite_result.json")


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
        "suite_id": f"MRS_{uuid.uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runners": results,
        "passed": passed,
        "total": total,
        "final_verdict": f"MACD_REBOUND_INTEGRATION_SUITE_{'PASS' if passed == total else 'FAIL'}|{passed}/{total}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(suite, indent=2), encoding="utf-8")
    print(f"suite: {passed}/{total} passed | verdict={suite['final_verdict']}")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
