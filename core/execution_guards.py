"""Pure execution-mode helpers and layered unlock assertions.

No subprocess, no network, no filesystem write, no trading/testnet imports.
All assertion functions raise on violation (fail-closed).
"""
from __future__ import annotations

import os
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# T601 — pure helpers
# ---------------------------------------------------------------------------

_KNOWN_MODES = frozenset({"dry-run", "dry_run", "testnet", "live"})


def normalize_execution_mode(mode: str | None) -> str:
    """Return a canonical execution mode string or raise ValueError."""
    raw = str(mode or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw not in _KNOWN_MODES:
        raise ValueError(f"unknown execution mode: {mode!r}")
    return raw


def read_bool_env(key: str, *, default: bool = False) -> bool:
    """Read a boolean from *os.environ* without touching the filesystem."""
    val = os.environ.get(key, "")
    text = str(val).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def parse_symbol_allowlist(raw: str | Sequence[str] | None) -> frozenset[str]:
    """Parse a symbol allowlist from a comma-separated string, list, or None."""
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = list(raw)
    return frozenset(s.strip().upper() for s in parts if s.strip())


def build_execution_guard_report(
    *,
    mode: str | None,
    action: str,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    env_overrides: dict[str, bool] | None = None,
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> dict[str, Any]:
    """Return a structured dict describing the current guard state."""
    env = env_overrides or {}
    return {
        "mode": str(mode or ""),
        "action": action,
        "symbol": symbol.upper(),
        "symbol_allowlist": sorted(symbol_allowlist),
        "layer0_blocked": any(env.get(k, False) for k in _action_block_keys(action)),
        "layer1_capability": capability,
        "layer2_cli_allow": cli_allow,
        "layer3_env_unlock": env.get(_action_env_unlock_key(action), False),
        "layer4_manual_confirm": manual_confirm,
        "layer5_symbol_ok": (
            not symbol_allowlist or symbol.upper() in symbol_allowlist
        ),
    }


# ---------------------------------------------------------------------------
# T602 — layered unlock assertions
# ---------------------------------------------------------------------------

class ExecutionGuardError(Exception):
    """Raised when an execution guard check fails."""


def _action_block_keys(action: str) -> list[str]:
    return [f"QQ_NO_{action.upper()}"]


def _action_env_unlock_key(action: str) -> str:
    return f"QQ_UNLOCK_{action.upper()}"


def _assert_layer0(action: str) -> None:
    """Layer 0: QQ_NO_* kill-switch."""
    key = f"QQ_NO_{action.upper()}"
    if read_bool_env(key):
        raise ExecutionGuardError(f"layer0: {key} is set — {action} blocked")


def _assert_mode_known(mode: str | None) -> str:
    """Fail-closed if mode is unknown or missing."""
    return normalize_execution_mode(mode)


def assert_no_live_mode(mode: str | None) -> str:
    """Assert mode is not live. Returns the normalised mode."""
    resolved = _assert_mode_known(mode)
    if resolved == "live":
        raise ExecutionGuardError("live mode not allowed")
    return resolved


def assert_dry_run_required(mode: str | None) -> str:
    """Assert mode is exactly dry-run. Returns the normalised mode."""
    resolved = _assert_mode_known(mode)
    if resolved != "dry_run":
        raise ExecutionGuardError(f"dry_run required, got {resolved!r}")
    return resolved


def _assert_unlock_layers(
    action: str,
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    """Common layered-unlock check. Returns normalised mode on success."""
    resolved = _assert_mode_known(mode)
    _assert_layer0(action)

    # Layer 1: capability flag
    if not capability:
        raise ExecutionGuardError(
            f"layer1: capability flag missing for {action}"
        )

    # Layer 2: CLI allow flag
    if not cli_allow:
        raise ExecutionGuardError(
            f"layer2: CLI allow flag missing for {action}"
        )

    # Layer 3: env unlock
    if not read_bool_env(_action_env_unlock_key(action)):
        raise ExecutionGuardError(
            f"layer3: {_action_env_unlock_key(action)} not set for {action}"
        )

    # Layer 4: manual confirm
    if not manual_confirm:
        raise ExecutionGuardError(
            f"layer4: manual confirm required for {action}"
        )

    # Layer 5: symbol allowlist
    if symbol_allowlist and symbol.upper() not in symbol_allowlist:
        raise ExecutionGuardError(
            f"layer5: {symbol.upper()} not in allowlist"
        )

    return resolved


def assert_submit_unlocked(
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    return _assert_unlock_layers(
        "submit",
        mode=mode,
        symbol=symbol,
        symbol_allowlist=symbol_allowlist,
        capability=capability,
        cli_allow=cli_allow,
        manual_confirm=manual_confirm,
    )


def assert_cancel_unlocked(
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    return _assert_unlock_layers(
        "cancel",
        mode=mode,
        symbol=symbol,
        symbol_allowlist=symbol_allowlist,
        capability=capability,
        cli_allow=cli_allow,
        manual_confirm=manual_confirm,
    )


def assert_flatten_unlocked(
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    return _assert_unlock_layers(
        "flatten",
        mode=mode,
        symbol=symbol,
        symbol_allowlist=symbol_allowlist,
        capability=capability,
        cli_allow=cli_allow,
        manual_confirm=manual_confirm,
    )


def assert_symbol_allowed(
    symbol: str,
    symbol_allowlist: frozenset[str] | None,
) -> str:
    """Assert symbol is in allowlist. Empty allowlist = all allowed."""
    resolved = symbol.strip().upper()
    if symbol_allowlist and resolved not in symbol_allowlist:
        raise ExecutionGuardError(
            f"layer5: {resolved} not in symbol allowlist"
        )
    return resolved
