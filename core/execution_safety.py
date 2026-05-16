from __future__ import annotations

from typing import Any, Mapping


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def validate_execution_safety(
    env: str,
    submit_mode: str,
    allow_testnet_submit: bool = False,
    allow_live_submit: bool = False,
    live_confirm_phrase: str = "",
    config: Mapping[str, Any] | None = None,
    symbol: str = "",
    max_notional_usdt: float = 0.0,
    risk_per_trade_pct: float = 0.0,
) -> dict[str, Any]:
    resolved_env = str(env or "").strip().lower()
    resolved_mode = str(submit_mode or "").strip().lower()
    resolved_symbol = str(symbol or "").strip().upper()

    if resolved_env not in {"testnet", "live"}:
        return {
            "allowed": False,
            "reason": "env_not_supported",
            "severity": "CRITICAL",
        }

    if resolved_env == "testnet":
        if "testnet" not in resolved_mode:
            return {
                "allowed": False,
                "reason": "submit_mode_env_mismatch",
                "severity": "ERROR",
            }
        if not bool(allow_testnet_submit):
            return {
                "allowed": False,
                "reason": "testnet_submit_not_allowed",
                "severity": "WARNING",
            }
        return {
            "allowed": True,
            "reason": "allowed_testnet_submit",
            "severity": "INFO",
        }

    # live
    if resolved_mode != "live":
        return {
            "allowed": False,
            "reason": "submit_mode_env_mismatch",
            "severity": "CRITICAL",
        }
    if not bool(allow_live_submit):
        return {
            "allowed": False,
            "reason": "allow_live_submit_false",
            "severity": "CRITICAL",
        }
    if config is None:
        return {
            "allowed": False,
            "reason": "missing_live_config",
            "severity": "CRITICAL",
        }

    safety = dict(config.get("execution_safety", {})) if isinstance(config, Mapping) else {}
    live_enabled = _to_bool(safety.get("live_trading_enabled", False), False)
    if not live_enabled:
        return {
            "allowed": False,
            "reason": "live_trading_disabled",
            "severity": "CRITICAL",
        }

    phrase_expected = str(safety.get("live_confirm_phrase", "I_UNDERSTAND_THIS_IS_REAL_MONEY")).strip()
    if str(live_confirm_phrase or "").strip() != phrase_expected:
        return {
            "allowed": False,
            "reason": "live_confirm_phrase_mismatch",
            "severity": "CRITICAL",
        }

    allowlist = [str(item or "").strip().upper() for item in safety.get("live_allowlist", []) if str(item or "").strip()]
    if allowlist and resolved_symbol and resolved_symbol not in set(allowlist):
        return {
            "allowed": False,
            "reason": "symbol_not_in_live_allowlist",
            "severity": "CRITICAL",
        }

    limit_notional = _to_float(safety.get("live_max_notional_usdt", 0.0), 0.0)
    if _to_float(max_notional_usdt, 0.0) > limit_notional:
        return {
            "allowed": False,
            "reason": "live_notional_exceeds_limit",
            "severity": "CRITICAL",
        }

    limit_risk_pct = _to_float(safety.get("live_max_risk_per_trade_pct", 0.0), 0.0)
    if _to_float(risk_per_trade_pct, 0.0) > limit_risk_pct:
        return {
            "allowed": False,
            "reason": "live_risk_pct_exceeds_limit",
            "severity": "CRITICAL",
        }

    return {
        "allowed": True,
        "reason": "allowed_live_submit",
        "severity": "INFO",
    }
