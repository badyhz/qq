"""Runner: paper ops state audit."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_ops.paper_state_auditor import audit_store
from src.paper_trading_pipeline.paper_position_store import DEFAULT_STORE_PATH

OUT = pathlib.Path("reports/paper_trading_ops/state_audit.json")


def main() -> None:
    report = audit_store(DEFAULT_STORE_PATH)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"status={report.audit_status} total={report.records_total} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
