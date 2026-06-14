"""Runner: paper ops runtime layout check."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.runtime_layout import check_layout
from src.paper_trading_deployment.server_config import build_server_config

OUT = pathlib.Path("reports/paper_trading_deployment/runtime_layout.json")


def main() -> None:
    cfg = build_server_config()
    report = check_layout(cfg.repo_path)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    print(f"status={report.layout_status} existing={len(report.existing_dirs)} missing={len(report.missing_dirs)} verdict={report.final_verdict}")


if __name__ == "__main__":
    main()
