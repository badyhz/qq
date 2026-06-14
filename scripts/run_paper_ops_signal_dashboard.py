"""Runner: paper ops signal quality dashboard."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_ops.signal_quality_dashboard import build_dashboard
from src.paper_trading_ops.strategy_quality_metrics import compute_metrics
from src.paper_trading_pipeline.paper_position_store import load_store

OUT = pathlib.Path("reports/paper_trading_ops/signal_dashboard.json")


def main() -> None:
    records = load_store()
    positions = [r.to_dict() for r in records]
    metrics = compute_metrics(positions)
    dashboard = build_dashboard(
        raw_signals=0, deduped_signals=0, plans_created=0, plans_rejected=0,
        positions=positions, expectancy_r=metrics.expectancy_r, win_rate=metrics.win_rate,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dashboard.to_dict(), indent=2), encoding="utf-8")
    print(f"grade={dashboard.quality_grade} closed={dashboard.closed_positions} verdict={dashboard.final_verdict}")


if __name__ == "__main__":
    main()
