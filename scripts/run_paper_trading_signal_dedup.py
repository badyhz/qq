"""Runner: paper trading signal dedup."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_pipeline.scanner_log_source import load_scanner_snapshot
from src.paper_trading_pipeline.signal_deduplicator import deduplicate_signals
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_log_ingest import _read_csv, _read_jsonl

OUT = pathlib.Path("reports/paper_trading/signal_dedup.json")


def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    root = pathlib.Path(cfg.local_path)
    signals = _read_csv(root / "data" / "signals.csv")
    alerts = _read_jsonl(root / "logs" / "alerts.jsonl")
    batch = deduplicate_signals(signals, alerts)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(batch.to_dict(), indent=2), encoding="utf-8")
    print(f"raw={batch.raw_count} deduped={batch.deduped_count} dup={batch.duplicate_count} verdict={batch.final_verdict}")


if __name__ == "__main__":
    main()
