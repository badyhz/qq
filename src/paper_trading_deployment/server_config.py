"""Server config — loads and validates deployment config."""
from __future__ import annotations
import pathlib, yaml
from src.paper_trading_deployment.models import ServerConfig, new_id, utc_now_iso

CONFIG_CANDIDATES = (
    "config/deployments/paper_trading_ops_server.example.yaml",
    "config/deployments/paper_trading_ops_server.yaml",
)

SAFETY_KEYS = (
    "real_order_submit_allowed", "real_trading_allowed",
    "real_feishu_send_allowed", "private_exchange_api_allowed",
    "systemd_auto_install_allowed", "crontab_auto_write_allowed",
)


def _find_config() -> pathlib.Path | None:
    for c in CONFIG_CANDIDATES:
        p = pathlib.Path(c)
        if p.exists():
            return p
    return None


def load_config(config_path: str | None = None) -> dict:
    if config_path:
        p = pathlib.Path(config_path)
    else:
        p = _find_config()
    if not p or not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_repo_path(cfg: dict) -> str:
    candidates = cfg.get("server", {}).get("qq_repo_path_candidates", [])
    for c in candidates:
        if pathlib.Path(c).exists():
            return c
    return candidates[0] if candidates else str(pathlib.Path.cwd())


def resolve_scanner_path(cfg: dict) -> str:
    candidates = cfg.get("server", {}).get("scanner_path_candidates", [])
    for c in candidates:
        if pathlib.Path(c).exists():
            return c
    return candidates[0] if candidates else ""


def build_server_config(config_path: str | None = None) -> ServerConfig:
    cfg = load_config(config_path)
    server = cfg.get("server", {})
    runtime = cfg.get("runtime", {})
    schedule = cfg.get("schedule", {})
    safety = cfg.get("safety", {})

    repo = resolve_repo_path(cfg)
    scanner = resolve_scanner_path(cfg)

    safety_flags = {k: safety.get(k, False) for k in SAFETY_KEYS}
    all_false = all(v is False for v in safety_flags.values())

    return ServerConfig(
        config_id=new_id("SCF"), created_at=utc_now_iso(),
        deployment_name=cfg.get("deployment_name", "paper_trading_ops_server"),
        mode=cfg.get("mode", "dry_run_only"),
        host_alias=server.get("host_alias", "unknown"),
        repo_path=repo, scanner_path=scanner,
        paper_positions_path=runtime.get("paper_positions_path",
            "data/runtime/paper_trading_pipeline/paper_positions.jsonl"),
        reports_dir=runtime.get("reports_dir", "reports/paper_trading_ops"),
        logs_dir=runtime.get("logs_dir", "logs/paper_trading_ops"),
        schedule=schedule,
        safety_flags=safety_flags,
        final_verdict=(
            "PAPER_OPS_SERVER_CONFIG_READY|SAFETY_FLAGS_ALL_FALSE|REAL_ORDER_SUBMIT_NOT_ALLOWED"
            if all_false
            else "PAPER_OPS_SERVER_CONFIG_READY|SAFETY_FLAGS_NOT_ALL_FALSE|REVIEW_REQUIRED"
        ),
    )
