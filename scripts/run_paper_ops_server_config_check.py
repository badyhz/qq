"""Runner: paper ops server config check."""
from __future__ import annotations
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.paper_trading_deployment.server_config import build_server_config

OUT = pathlib.Path("reports/paper_trading_deployment/server_config.json")


def main() -> None:
    cfg = build_server_config()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    print(f"config={cfg.deployment_name} mode={cfg.mode} host={cfg.host_alias} verdict={cfg.final_verdict}")


if __name__ == "__main__":
    main()
