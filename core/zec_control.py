"""Governed runtime controls for the ZEC live strategy.

The control plane owns configuration only.  It has no order-submission API and
cannot mutate strategy/execution state.  Runtime documents are atomically
replaced and every accepted change is appended to a local audit trail.

Two revisions are intentionally separated:
- ``control_revision`` is an optimistic-concurrency token and increments for
  every accepted UI mutation, including strategy ON/OFF.
- ``revision`` is the execution-identity revision and increments only when
  strategy/symbol/timeframe/sizing changes.  A plain ON/OFF toggle therefore
  never resets scorecard/ledger continuity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Optional


CONTROL_SCHEMA_VERSION = 1
DEFAULT_CONTROL_DIR = Path("/var/lib/quant-shadow/zec-control")
DEFAULT_CONFIG_PATH = DEFAULT_CONTROL_DIR / "runtime_config.json"
DEFAULT_AUDIT_PATH = DEFAULT_CONTROL_DIR / "audit.jsonl"

FIXED_CAPITAL_CAP_USDT = 50.0
FIXED_LEVERAGE = 50
DEFAULT_STRATEGY_ID = "zec_4h_live_v1"
DEFAULT_SYMBOL = "ZECUSDT"
DEFAULT_TIMEFRAME = "4h"
DEFAULT_SIZING_BASE_USDT = 0.5

TIMEFRAME_SECONDS: dict[str, int] = {
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
    "2h": 2 * 60 * 60,
    "4h": 4 * 60 * 60,
    "6h": 6 * 60 * 60,
    "8h": 8 * 60 * 60,
    "12h": 12 * 60 * 60,
    "1d": 24 * 60 * 60,
}

STRATEGY_REGISTRY: dict[str, dict[str, Any]] = {
    DEFAULT_STRATEGY_ID: {
        "name": "ZEC 4H long-only",
        "display_name": "ZEC 4H long-only",
        "strategy_factory": "core.zec_4h_live:Zec4hStrategy",
        "allowed_symbols": "USDT_PERPETUAL",
        "direction": "LONG_ONLY",
        "allowed_timeframes": tuple(TIMEFRAME_SECONDS),
        "quote_asset": "USDT",
        "contract_type": "PERPETUAL",
    }
}


class ControlConflictError(RuntimeError):
    """Raised when a stale UI revision attempts to replace current config."""


class UnsafeConfigurationChange(RuntimeError):
    """Raised when an identity/sizing change is attempted across live state."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class RuntimeConfig:
    schema_version: int = CONTROL_SCHEMA_VERSION
    # Execution identity.  Only settings changes advance this value.
    revision: int = 1
    # UI/API optimistic concurrency token.  Every accepted mutation advances it.
    control_revision: int = 1
    strategy_enabled: bool = False
    strategy_id: str = DEFAULT_STRATEGY_ID
    symbol: str = DEFAULT_SYMBOL
    timeframe: str = DEFAULT_TIMEFRAME
    sizing_base_usdt: float = DEFAULT_SIZING_BASE_USDT
    capital_cap_usdt: float = FIXED_CAPITAL_CAP_USDT
    leverage: int = FIXED_LEVERAGE
    risk_increase_after_bar_close_time: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Optional[Mapping[str, Any]]) -> "RuntimeConfig":
        values = dict(raw or {})
        allowed = set(cls.__dataclass_fields__)
        config = cls(**{key: value for key, value in values.items() if key in allowed})
        return validate_runtime_config(config)


def validate_runtime_config(config: RuntimeConfig) -> RuntimeConfig:
    if not isinstance(config.strategy_enabled, bool):
        raise ValueError("strategy_enabled must be boolean")
    if isinstance(config.revision, bool):
        raise ValueError("runtime config revision must be an integer")
    if isinstance(config.control_revision, bool):
        raise ValueError("runtime control revision must be an integer")
    if isinstance(config.sizing_base_usdt, bool):
        raise ValueError("sizing_base_usdt must be numeric")
    strategy_id = str(config.strategy_id).strip()
    symbol = str(config.symbol).strip().upper()
    timeframe = str(config.timeframe).strip().lower()
    if config.schema_version != CONTROL_SCHEMA_VERSION:
        raise ValueError("unsupported runtime config schema")
    if int(config.revision) < 1:
        raise ValueError("runtime config revision must be positive")
    if int(config.control_revision) < 1:
        raise ValueError("runtime control revision must be positive")
    if strategy_id not in STRATEGY_REGISTRY:
        raise ValueError("unknown strategy_id")
    registry = STRATEGY_REGISTRY[strategy_id]
    if timeframe not in registry["allowed_timeframes"]:
        raise ValueError("unsupported timeframe")
    if not symbol.endswith(str(registry["quote_asset"])):
        raise ValueError("symbol must use the registered quote asset")
    sizing = float(config.sizing_base_usdt)
    if not math.isfinite(sizing) or sizing <= 0 or sizing > FIXED_CAPITAL_CAP_USDT:
        raise ValueError("sizing_base_usdt outside governed capital boundary")
    if float(config.capital_cap_usdt) != FIXED_CAPITAL_CAP_USDT:
        raise ValueError("capital_cap_usdt is immutable")
    if int(config.leverage) != FIXED_LEVERAGE:
        raise ValueError("leverage is immutable")
    return replace(
        config,
        revision=int(config.revision),
        control_revision=int(config.control_revision),
        strategy_enabled=bool(config.strategy_enabled),
        strategy_id=strategy_id,
        symbol=symbol,
        timeframe=timeframe,
        sizing_base_usdt=sizing,
        capital_cap_usdt=FIXED_CAPITAL_CAP_USDT,
        leverage=FIXED_LEVERAGE,
        risk_increase_after_bar_close_time=str(config.risk_increase_after_bar_close_time or ""),
        updated_at=str(config.updated_at or ""),
    )


def validate_exchange_symbol(config: RuntimeConfig, exchange_info: Mapping[str, Any]) -> dict[str, Any]:
    """Prove that a configured symbol is a live USDT perpetual contract."""
    symbols = exchange_info.get("symbols")
    if not isinstance(symbols, list):
        raise ValueError("malformed exchangeInfo response")
    for item in symbols:
        if not isinstance(item, Mapping) or str(item.get("symbol", "")).upper() != config.symbol:
            continue
        if str(item.get("status", "")).upper() != "TRADING":
            raise ValueError("configured symbol is not trading")
        if str(item.get("quoteAsset", "")).upper() != "USDT":
            raise ValueError("configured symbol is not USDT quoted")
        contract_type = str(item.get("contractType", "")).upper()
        if contract_type != "PERPETUAL":
            raise ValueError("configured symbol is not perpetual")
        return dict(item)
    raise ValueError("configured symbol not present in exchangeInfo")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_runtime_config(path: Path, config: RuntimeConfig) -> None:
    config = validate_runtime_config(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(config.to_dict(), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_runtime_config(
    path: Path = DEFAULT_CONFIG_PATH,
    *,
    create: bool = False,
    initial_strategy_enabled: bool = False,
) -> RuntimeConfig:
    if not path.exists():
        config = RuntimeConfig(
            strategy_enabled=bool(initial_strategy_enabled),
            updated_at=utc_now(),
        )
        if create:
            write_runtime_config(path, config)
        return config
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("runtime config must be a JSON object")
    return RuntimeConfig.from_dict(payload)


def append_audit(path: Path, event: Mapping[str, Any]) -> None:
    """Append a secret-free control event and force it to stable storage."""
    forbidden = {"api_key", "api_secret", "secret", "password", "authorization"}
    normalized = {str(key): value for key, value in event.items() if str(key).lower() not in forbidden}
    normalized.setdefault("recorded_at", utc_now())
    line = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(path, 0o600)


def identity_changed(before: RuntimeConfig, after: RuntimeConfig) -> bool:
    return any((
        before.strategy_id != after.strategy_id,
        before.symbol != after.symbol,
        before.timeframe != after.timeframe,
        before.sizing_base_usdt != after.sizing_base_usdt,
    ))


def update_runtime_config(
    path: Path,
    *,
    expected_revision: int,
    changes: Mapping[str, Any],
    audit_path: Path = DEFAULT_AUDIT_PATH,
    actor: str = "admin",
) -> RuntimeConfig:
    current = load_runtime_config(path, create=True)
    if int(expected_revision) != current.control_revision:
        raise ControlConflictError("runtime config revision conflict")
    immutable = {
        "schema_version",
        "revision",
        "control_revision",
        "capital_cap_usdt",
        "leverage",
        "updated_at",
    }
    if immutable.intersection(changes):
        raise ValueError("attempted mutation of governed runtime field")
    allowed = {
        "strategy_enabled",
        "strategy_id",
        "symbol",
        "timeframe",
        "sizing_base_usdt",
        "risk_increase_after_bar_close_time",
    }
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"unknown runtime field: {sorted(unknown)[0]}")

    proposed = validate_runtime_config(replace(current, **dict(changes)))
    next_execution_revision = current.revision + 1 if identity_changed(current, proposed) else current.revision
    candidate = validate_runtime_config(replace(
        proposed,
        revision=next_execution_revision,
        control_revision=current.control_revision + 1,
        updated_at=utc_now(),
    ))
    write_runtime_config(path, candidate)
    append_audit(audit_path, {
        "event": "RUNTIME_CONFIG_UPDATED",
        "action": "RUNTIME_CONFIG_UPDATED",
        "actor": actor,
        "from_control_revision": current.control_revision,
        "to_control_revision": candidate.control_revision,
        "old_revision": current.control_revision,
        "new_revision": candidate.control_revision,
        "from_execution_revision": current.revision,
        "to_execution_revision": candidate.revision,
        "changed_fields": sorted(changes),
        "before": current.to_dict(),
        "after": candidate.to_dict(),
        "old_config": current.to_dict(),
        "new_config": candidate.to_dict(),
        "result": "PASS",
    })
    return candidate


def assert_safe_configuration_change(
    before: RuntimeConfig,
    after: RuntimeConfig,
    *,
    position_qty: float,
    open_order_count: int,
    pending_action: str,
    recovery_status: str,
) -> None:
    if not identity_changed(before, after):
        return
    blockers = []
    if abs(float(position_qty)) > 0:
        blockers.append("POSITION_OPEN")
    if int(open_order_count) > 0:
        blockers.append("OPEN_ORDERS")
    if str(pending_action).strip():
        blockers.append("PENDING_ACTION")
    if str(recovery_status).strip():
        blockers.append("RECOVERY_ACTIVE")
    if blockers:
        raise UnsafeConfigurationChange(",".join(blockers))


def timeframe_seconds(timeframe: str) -> int:
    try:
        return TIMEFRAME_SECONDS[str(timeframe).lower()]
    except KeyError as exc:
        raise ValueError("unsupported timeframe") from exc
