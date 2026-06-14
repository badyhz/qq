"""Runner: trade plan replay evaluator."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.trade_plan_engine.replay_evaluator import evaluate, write_stats, render_report
from src.trade_plan_engine.models import PaperPosition

OUT = pathlib.Path("reports/trade_plan/replay_evaluator.json")
MD = pathlib.Path("reports/trade_plan/replay_evaluator.md")


def main() -> None:
    # Demo with empty positions — real usage would load from lifecycle output
    positions: list[PaperPosition] = []
    stats = evaluate(positions)
    write_stats(stats, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(stats), encoding="utf-8")
    print(f"total={stats.total_plans} win_rate={stats.win_rate}% verdict={stats.final_verdict}")


if __name__ == "__main__":
    main()
