from __future__ import annotations

from typing import Any


def resolve_live_safety_switch(config: dict[str, Any], override: Any = None) -> bool:
    if override is not None:
        return bool(override)
    execution_cfg = config.get("execution", {}) if isinstance(config, dict) else {}
    return bool(execution_cfg.get("enable_live_trading", False))
