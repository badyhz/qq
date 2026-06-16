"""Paper runtime config — local paper-only configuration, no network."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str = "paper_only"
    strategy_name: str = "macd_rebound"
    fixture_paths: List[str] = field(default_factory=list)
    output_dir: str = "reports"
    max_risk_per_trade_pct: float = 1.0
    max_position_pct: float = 10.0
    min_rr_ratio: float = 1.5
    max_open_plans: int = 5
    max_total_exposure: float = 50000.0
    max_daily_loss: float = 50000.0
    enable_local_alerts: bool = True
    enable_html_report: bool = True

    def __post_init__(self):
        if self.mode != "paper_only":
            raise ValueError(f"mode must be 'paper_only', got '{self.mode}'")
        if not self.strategy_name:
            raise ValueError("strategy_name required")
        if self.max_risk_per_trade_pct <= 0 or self.max_risk_per_trade_pct > 100:
            raise ValueError(f"max_risk_per_trade_pct must be 0-100, got {self.max_risk_per_trade_pct}")
        if self.max_position_pct <= 0 or self.max_position_pct > 100:
            raise ValueError(f"max_position_pct must be 0-100, got {self.max_position_pct}")
        if self.min_rr_ratio <= 0:
            raise ValueError(f"min_rr_ratio must be positive, got {self.min_rr_ratio}")


def load_config_from_dict(data: dict) -> RuntimeConfig:
    """Load config from a dict (e.g. parsed JSON)."""
    return RuntimeConfig(
        mode=data.get("mode", "paper_only"),
        strategy_name=data.get("strategy_name", "macd_rebound"),
        fixture_paths=data.get("fixture_paths", []),
        output_dir=data.get("output_dir", "reports"),
        max_risk_per_trade_pct=float(data.get("max_risk_per_trade_pct", 1.0)),
        max_position_pct=float(data.get("max_position_pct", 10.0)),
        min_rr_ratio=float(data.get("min_rr_ratio", 1.5)),
        max_open_plans=int(data.get("max_open_plans", 5)),
        max_total_exposure=float(data.get("max_total_exposure", 50000.0)),
        max_daily_loss=float(data.get("max_daily_loss", 50000.0)),
        enable_local_alerts=bool(data.get("enable_local_alerts", True)),
        enable_html_report=bool(data.get("enable_html_report", True)),
    )


def load_config_from_json(path: str) -> RuntimeConfig:
    """Load config from a JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return load_config_from_dict(data)


def default_config(fixture_paths: Optional[List[str]] = None) -> RuntimeConfig:
    """Return default config with optional fixture paths."""
    return RuntimeConfig(fixture_paths=fixture_paths or [])
