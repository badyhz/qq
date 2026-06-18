"""Strategy configuration loader — reads strategies.yaml and validates safety constraints.

No secrets, no webhooks, no order paths.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml


SAFETY_REQUIRED = {
    "mode": "paper",
    "auto_send": False,
}

SAFETY_DATA_API_REQUIRED = {
    "readonly": True,
    "requires_secret": False,
    "allows_orders": False,
}


@dataclass(frozen=True)
class DataApiConfig:
    name: str
    api_type: str
    market: str
    readonly: bool
    requires_secret: bool
    allows_orders: bool
    default_limit: int


@dataclass(frozen=True)
class AlertConfig:
    feishu_payload: bool
    auto_send: bool


@dataclass(frozen=True)
class StrategyConfig:
    strategy_id: str
    strategy_type: str
    description: str
    enabled: bool
    data_api: str
    symbols: list[str]
    timeframes: list[str]
    mode: str
    alert: AlertConfig


@dataclass(frozen=True)
class StrategyLibrary:
    version: int
    default_mode: str
    default_alert: str
    data_apis: dict[str, DataApiConfig]
    strategies: dict[str, StrategyConfig]
    enabled_strategies: dict[str, StrategyConfig]
    disabled_strategies: dict[str, StrategyConfig]


def load_strategy_config(config_path: str) -> StrategyLibrary:
    """Load and validate strategy configuration from YAML file."""
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Strategy config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError("Config must be a YAML dict")

    version = int(raw.get("version", 1))
    default_mode = str(raw.get("default_mode", "paper"))
    default_alert = str(raw.get("default_alert", "feishu_payload_only"))

    # Parse data APIs
    data_apis: dict[str, DataApiConfig] = {}
    for api_name, api_raw in raw.get("data_apis", {}).items():
        api = _parse_data_api(api_name, api_raw)
        data_apis[api_name] = api

    # Parse strategies
    strategies: dict[str, StrategyConfig] = {}
    for strat_id, strat_raw in raw.get("strategies", {}).items():
        strat = _parse_strategy(strat_id, strat_raw, data_apis)
        strategies[strat_id] = strat

    enabled = {k: v for k, v in strategies.items() if v.enabled}
    disabled = {k: v for k, v in strategies.items() if not v.enabled}

    return StrategyLibrary(
        version=version,
        default_mode=default_mode,
        default_alert=default_alert,
        data_apis=data_apis,
        strategies=strategies,
        enabled_strategies=enabled,
        disabled_strategies=disabled,
    )


def _parse_data_api(name: str, raw: dict[str, Any]) -> DataApiConfig:
    """Parse and validate a data API config."""
    api_type = str(raw.get("type", ""))
    market = str(raw.get("market", ""))
    readonly = bool(raw.get("readonly", False))
    requires_secret = bool(raw.get("requires_secret", True))
    allows_orders = bool(raw.get("allows_orders", True))
    default_limit = int(raw.get("default_limit", 120))

    # Safety validation
    if not readonly:
        raise ValueError(f"Data API '{name}' must be readonly=true")
    if requires_secret:
        raise ValueError(f"Data API '{name}' must not require secret")
    if allows_orders:
        raise ValueError(f"Data API '{name}' must not allow orders")

    return DataApiConfig(
        name=name,
        api_type=api_type,
        market=market,
        readonly=readonly,
        requires_secret=requires_secret,
        allows_orders=allows_orders,
        default_limit=default_limit,
    )


def _parse_strategy(strat_id: str, raw: dict[str, Any], data_apis: dict[str, DataApiConfig]) -> StrategyConfig:
    """Parse and validate a strategy config."""
    strategy_type = str(raw.get("strategy_type", strat_id))
    description = str(raw.get("description", ""))
    enabled = bool(raw.get("enabled", False))
    data_api_name = str(raw.get("data_api", ""))
    symbols = list(raw.get("symbols", []))
    timeframes = list(raw.get("timeframes", []))
    mode = str(raw.get("mode", "paper"))

    # Parse alert config
    alert_raw = raw.get("alert", {})
    alert = AlertConfig(
        feishu_payload=bool(alert_raw.get("feishu_payload", True)),
        auto_send=bool(alert_raw.get("auto_send", False)),
    )

    # Safety validation
    if mode != "paper":
        raise ValueError(f"Strategy '{strat_id}' must use mode=paper, got {mode}")
    if alert.auto_send:
        raise ValueError(f"Strategy '{strat_id}' must not have auto_send=true")

    # Validate data API exists and is safe
    if data_api_name not in data_apis:
        raise ValueError(f"Strategy '{strat_id}' references unknown data_api: {data_api_name}")
    api = data_apis[data_api_name]
    if not api.readonly:
        raise ValueError(f"Strategy '{strat_id}' data_api must be readonly")
    if api.requires_secret:
        raise ValueError(f"Strategy '{strat_id}' data_api must not require secret")
    if api.allows_orders:
        raise ValueError(f"Strategy '{strat_id}' data_api must not allow orders")

    # Validate symbols
    if not symbols:
        raise ValueError(f"Strategy '{strat_id}' must have at least one symbol")

    # Validate timeframes
    if not timeframes:
        raise ValueError(f"Strategy '{strat_id}' must have at least one timeframe")

    return StrategyConfig(
        strategy_id=strat_id,
        strategy_type=strategy_type,
        description=description,
        enabled=enabled,
        data_api=data_api_name,
        symbols=symbols,
        timeframes=timeframes,
        mode=mode,
        alert=alert,
    )
