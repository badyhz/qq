"""Runner: paper ops rollback plan (does not execute)."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.rollback_plan import create_rollback_plan

OUT = pathlib.Path("reports/paper_trading_deployment/rollback_plan.json")


def main() -> None:
    plan = create_rollback_plan()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
    print(f"manual_confirmation={plan.manual_confirmation_required} verdict={plan.final_verdict}")


if __name__ == "__main__":
    main()
