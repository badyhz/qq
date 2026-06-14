"""Runner: daily trade plan review."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.trade_plan_engine.daily_trade_plan_review import generate_review, write_review, render_report

OUT = pathlib.Path("reports/trade_plan/daily_review.json")
MD = pathlib.Path("reports/trade_plan/daily_review.md")


def main() -> None:
    # Demo with empty data — real usage would load from plan/lifecycle outputs
    review = generate_review(signal_count=0, plans=[], positions=[])
    write_review(review, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(review), encoding="utf-8")
    print(f"signals={review.total_signals} plans={review.total_trade_plans} verdict={review.final_verdict}")


if __name__ == "__main__":
    main()
