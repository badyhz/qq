"""Runner: MACD rebound log ingest."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_log_ingest import ingest_logs, write_result, render_report

OUT = pathlib.Path("reports/macd_rebound/log_ingest.json")
MD = pathlib.Path("reports/macd_rebound/log_ingest.md")

def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    result = ingest_logs(cfg.local_path)
    write_result(result, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(result), encoding="utf-8")
    print(f"signals={result.total_signals} alerts={result.total_alerts} errors={result.error_count} verdict={result.final_verdict}")

if __name__ == "__main__":
    main()
