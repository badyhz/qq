#!/usr/bin/env python3
"""T72501 — Runtime Observability Report."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.observability.runtime_metrics import collect_metrics, write_metrics
from src.runtime_integrations.observability.runtime_health import evaluate_health, write_health

def main():
    metrics = collect_metrics(ROOT / "data", ROOT / "reports")
    write_metrics(metrics, ROOT / "data" / "runtime" / "observability" / "runtime_metrics.json")
    health = evaluate_health(metrics)
    write_health(health, ROOT / "data" / "runtime" / "observability" / "runtime_health.json")
    print(f"Observability: health={health.status}, signals={metrics.signal_count}, alerts={metrics.alert_count}")

if __name__ == "__main__":
    main()
