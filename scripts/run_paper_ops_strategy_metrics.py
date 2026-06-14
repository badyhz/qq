"""Runner: paper ops strategy quality metrics."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_ops.strategy_quality_metrics import compute_metrics
from src.paper_trading_pipeline.paper_position_store import load_store

OUT = pathlib.Path("reports/paper_trading_ops/strategy_metrics.json")


def main() -> None:
    records = load_store()
    positions = [r.to_dict() for r in records]
    metrics = compute_metrics(positions)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(metrics.to_dict(), indent=2), encoding="utf-8")
    print(f"sample={metrics.sample_status} win_rate={metrics.win_rate:.1f}% expectancy={metrics.expectancy_r:.2f}R verdict={metrics.final_verdict}")


if __name__ == "__main__":
    main()
