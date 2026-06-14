"""Runner: MACD rebound deployment audit."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.external_scanner_integrations.macd_rebound_config import create_config
from src.external_scanner_integrations.macd_rebound_deployment_audit import run_audit, write_audit, render_report

OUT = pathlib.Path("reports/macd_rebound/deployment_audit.json")
MD = pathlib.Path("reports/macd_rebound/deployment_audit.md")

def main() -> None:
    cfg = create_config()
    if not cfg.local_path:
        print("ERROR: scanner path not found")
        sys.exit(1)
    audit = run_audit(cfg.local_path)
    write_audit(audit, OUT)
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text(render_report(audit), encoding="utf-8")
    print(f"checks={len(audit.checks)} verdict={audit.final_verdict}")

if __name__ == "__main__":
    main()
