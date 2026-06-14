"""MACD rebound scanner configuration loader."""
from __future__ import annotations
import json, pathlib, uuid, yaml
from dataclasses import dataclass
from datetime import datetime, timezone

CONFIG_EXAMPLE = pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "external_scanners" / "macd_rebound_scanner.example.yaml"


@dataclass(frozen=True)
class ScannerConfig:
    config_id: str
    created_at: str
    scanner_name: str
    repo_url: str
    local_path: str | None
    local_path_found: bool
    expected_files_present: dict[str, bool]
    runtime_files_config: dict[str, str]
    default_mode: dict[str, bool]
    real_feishu_send_allowed: bool
    real_order_submit_allowed: bool
    final_verdict: str
    def to_dict(self) -> dict:
        return {"config_id": self.config_id, "created_at": self.created_at,
                "scanner_name": self.scanner_name, "repo_url": self.repo_url,
                "local_path": self.local_path, "local_path_found": self.local_path_found,
                "expected_files_present": self.expected_files_present,
                "runtime_files_config": self.runtime_files_config,
                "default_mode": self.default_mode,
                "real_feishu_send_allowed": self.real_feishu_send_allowed,
                "real_order_submit_allowed": self.real_order_submit_allowed,
                "final_verdict": self.final_verdict}


def load_example_config() -> dict:
    if CONFIG_EXAMPLE.exists():
        return yaml.safe_load(CONFIG_EXAMPLE.read_text(encoding="utf-8"))
    return {}


def detect_scanner_path(config: dict) -> str | None:
    candidates = config.get("local_path_candidates", [])
    for c in candidates:
        p = pathlib.Path(c)
        if p.exists() and (p / "main.py").exists():
            return str(p)
    return None


def check_expected_files(scanner_path: str, expected: list[str]) -> dict[str, bool]:
    root = pathlib.Path(scanner_path)
    return {f: (root / f).exists() for f in expected}


def create_config(config_path: str | None = None) -> ScannerConfig:
    if config_path:
        cfg = yaml.safe_load(pathlib.Path(config_path).read_text(encoding="utf-8"))
    else:
        cfg = load_example_config()
    local_path = detect_scanner_path(cfg)
    expected = cfg.get("expected_files", [])
    files_present = check_expected_files(local_path, expected) if local_path else {}
    all_present = all(files_present.values()) if files_present else False
    found = local_path is not None
    verdict_parts = ["MACD_REBOUND_CONFIG_READY"]
    if found:
        verdict_parts.append("SCANNER_PATH_FOUND")
    else:
        verdict_parts.append("SCANNER_PATH_NOT_FOUND")
    if all_present:
        verdict_parts.append("ALL_EXPECTED_FILES_PRESENT")
    verdict_parts.append("REAL_ORDER_SUBMIT_NOT_ALLOWED")
    return ScannerConfig(
        config_id=f"MRC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scanner_name=cfg.get("scanner_name", "macd_rebound_scanner"),
        repo_url=cfg.get("repo_url", ""),
        local_path=local_path,
        local_path_found=found,
        expected_files_present=files_present,
        runtime_files_config=cfg.get("runtime_files", {}),
        default_mode=cfg.get("default_mode", {}),
        real_feishu_send_allowed=cfg.get("real_feishu_send_allowed", False),
        real_order_submit_allowed=cfg.get("real_order_submit_allowed", False),
        final_verdict="|".join(verdict_parts),
    )


def write_config(config: ScannerConfig, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")


def render_report(config: ScannerConfig) -> str:
    lines = ["# MACD Rebound Scanner Config", "",
        f"**config_id={config.config_id}**",
        f"**scanner_name={config.scanner_name}**",
        f"**local_path={config.local_path or 'NOT_FOUND'}**",
        f"**local_path_found={config.local_path_found}**", "",
        "## Expected Files", "",
        "| File | Present |", "|------|:---:|"]
    for f, present in config.expected_files_present.items():
        lines.append(f"| {f} | {'Y' if present else 'N'} |")
    lines.extend(["", "## Safety", "",
        f"- real_feishu_send_allowed: {config.real_feishu_send_allowed}",
        f"- real_order_submit_allowed: {config.real_order_submit_allowed}", "",
        "## Conclusion", "", config.final_verdict, ""])
    return "\n".join(lines)
