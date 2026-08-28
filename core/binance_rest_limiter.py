"""Cross-process Binance REST rate guard with persistent IP-ban state.

The guard is deliberately conservative: one request may be in flight across
all cooperating processes, and the local one-minute budget is capped at ten
percent of Binance USD-M's documented 2,400 request-weight limit.  It never
retries an HTTP request.  HTTP 429/418 and Binance ``-1003`` are converted into
one shared cooldown so a worker restart cannot forget an IP ban.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import io
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Callable, Iterator, Mapping, Optional, TypeVar
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse


OFFICIAL_WEIGHT_LIMIT_PER_MINUTE = 2_400
GLOBAL_SAFE_WEIGHT_BUDGET = 240
DEFAULT_IN_FLIGHT_LEASE_SECONDS = 60.0
DEFAULT_429_COOLDOWN_SECONDS = 60.0
DEFAULT_418_COOLDOWN_SECONDS = 300.0
_BAN_UNTIL_RE = re.compile(r"(?:until|banned until)\s*(\d{10,13})", re.IGNORECASE)
_BINANCE_HOSTS = {
    "api.binance.com",
    "fapi.binance.com",
    "dapi.binance.com",
    "data-api.binance.vision",
}
_PUBLIC_MARKET_PATHS = {
    "/api/v3/depth",
    "/api/v3/exchangeInfo",
    "/api/v3/klines",
    "/api/v3/ping",
    "/api/v3/ticker/24hr",
    "/api/v3/ticker/bookTicker",
    "/api/v3/time",
    "/fapi/v1/depth",
    "/fapi/v1/exchangeInfo",
    "/fapi/v1/fundingRate",
    "/fapi/v1/klines",
    "/fapi/v1/ping",
    "/fapi/v1/premiumIndex",
    "/fapi/v1/ticker/24hr",
    "/fapi/v1/ticker/bookTicker",
    "/fapi/v1/time",
}
T = TypeVar("T")


class BinanceRestBlocked(RuntimeError):
    """Raised before HTTP when the shared budget/cooldown denies a request."""

    def __init__(self, reason: str, *, retry_at: float = 0.0):
        super().__init__(reason)
        self.reason = reason
        self.retry_at = float(retry_at)


def _now_iso(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="milliseconds")


def _header(headers: Mapping[str, Any] | None, name: str) -> str:
    if headers is None:
        return ""
    target = name.lower()
    for key, value in headers.items():
        if str(key).lower() == target:
            return str(value or "")
    return ""


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _default_state_path() -> Path:
    configured = os.environ.get("BINANCE_REST_LIMIT_STATE_PATH", "").strip()
    if configured:
        return Path(configured)
    production = Path("/var/lib/quant-shadow")
    if production.is_dir() and os.access(production, os.W_OK):
        return production / "binance_rest_limit.json"
    durable_fallback = Path("/var/tmp")
    if durable_fallback.is_dir() and os.access(durable_fallback, os.W_OK):
        return durable_fallback / f"quant-shadow-binance-rest-{os.getuid()}.json"
    return Path(tempfile.gettempdir()) / f"quant-shadow-binance-rest-{os.getuid()}.json"


def estimate_request_weight(url: str) -> int:
    """Return a conservative documented request weight for known market paths."""
    parsed = urlparse(str(url))
    path = parsed.path
    query = parse_qs(parsed.query)
    limit = int(_number((query.get("limit") or [0])[0], 0))
    if path == "/fapi/v1/klines":
        if limit < 100:
            return 1
        if limit < 500:
            return 2
        if limit <= 1_000:
            return 5
        return 10
    if path == "/api/v3/klines":
        return 2
    if path == "/fapi/v1/depth":
        if limit <= 50:
            return 2
        if limit <= 100:
            return 5
        if limit <= 500:
            return 10
        return 20
    if path == "/fapi/v1/ticker/24hr" and "symbol" not in query:
        return 40
    if path in {"/fapi/v1/exchangeInfo", "/api/v3/exchangeInfo"}:
        return 20
    if path in {
        "/api/v3/ping", "/api/v3/time", "/fapi/v1/ping", "/fapi/v1/time",
        "/fapi/v1/fundingRate", "/fapi/v1/ticker/bookTicker",
    }:
        return 1
    return 5


class BinanceRestLimiter:
    """A file-locked limiter shared by cooperating local processes."""

    def __init__(
        self,
        state_path: Path | str | None = None,
        *,
        safe_weight_budget: int = GLOBAL_SAFE_WEIGHT_BUDGET,
        clock: Callable[[], float] = time.time,
        in_flight_lease_seconds: float = DEFAULT_IN_FLIGHT_LEASE_SECONDS,
    ):
        self.state_path = Path(state_path) if state_path is not None else _default_state_path()
        self.lock_path = self.state_path.with_suffix(self.state_path.suffix + ".lock")
        self.safe_weight_budget = int(safe_weight_budget)
        self.clock = clock
        self.in_flight_lease_seconds = float(in_flight_lease_seconds)

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "ban_until": 0.0,
            "last_418_at": "",
            "last_error_code": "",
            "last_retry_after": 0.0,
            "used_weight": 0,
            "used_weight_1m": 0,
            "public_read_healthy": True,
            "probe_in_flight_until": 0.0,
            "request_in_flight_until": 0.0,
            "window": [],
        }

    @contextmanager
    def _locked_state(self) -> Iterator[dict[str, Any]]:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        os.chmod(self.lock_path, 0o600)
        try:
            with os.fdopen(fd, "r+", encoding="utf-8") as lock_handle:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                state = self._read_state()
                try:
                    yield state
                finally:
                    self._write_state(state)
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            raise

    def _read_state(self) -> dict[str, Any]:
        state = self._empty_state()
        if not self.state_path.exists():
            return state
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return state
        if isinstance(value, dict):
            state.update(value)
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.state_path)
        os.chmod(self.state_path, 0o600)

    def snapshot(self) -> dict[str, Any]:
        with self._locked_state() as state:
            return dict(state)

    def acquire(self, *, weight: int, health_probe: bool = False) -> None:
        now = float(self.clock())
        requested_weight = max(1, int(weight))
        with self._locked_state() as state:
            ban_until = _number(state.get("ban_until"))
            if now < ban_until:
                raise BinanceRestBlocked("BINANCE_IP_BANNED", retry_at=ban_until)

            healthy = bool(state.get("public_read_healthy", True))
            if ban_until > 0 and now >= ban_until and not healthy:
                probe_until = _number(state.get("probe_in_flight_until"))
                if not health_probe:
                    raise BinanceRestBlocked("BINANCE_RECOVERY_PROBE_REQUIRED")
                if probe_until > now:
                    raise BinanceRestBlocked("BINANCE_RECOVERY_PROBE_IN_FLIGHT", retry_at=probe_until)
                state["probe_in_flight_until"] = now + self.in_flight_lease_seconds

            in_flight_until = _number(state.get("request_in_flight_until"))
            if in_flight_until > now:
                raise BinanceRestBlocked("BINANCE_REQUEST_IN_FLIGHT", retry_at=in_flight_until)

            window = [
                row for row in list(state.get("window") or [])
                if isinstance(row, list) and len(row) == 2 and _number(row[0]) > now - 60.0
            ]
            used = sum(int(_number(row[1])) for row in window)
            if used + requested_weight > self.safe_weight_budget:
                retry_at = min((_number(row[0]) + 60.0 for row in window), default=now + 60.0)
                raise BinanceRestBlocked("BINANCE_LOCAL_WEIGHT_BUDGET_EXHAUSTED", retry_at=retry_at)
            window.append([now, requested_weight])
            state["window"] = window
            state["request_in_flight_until"] = now + self.in_flight_lease_seconds

    def observe(
        self,
        *,
        status_code: int | None,
        headers: Mapping[str, Any] | None = None,
        error_code: int | str | None = None,
        message: str = "",
        health_probe: bool = False,
    ) -> None:
        now = float(self.clock())
        status = int(status_code or 0)
        code = str(error_code if error_code is not None else "")
        retry_after = max(0.0, _number(_header(headers, "Retry-After")))
        used_1m = int(_number(_header(headers, "X-MBX-USED-WEIGHT-1M")))
        used = int(_number(_header(headers, "X-MBX-USED-WEIGHT")))
        match = _BAN_UNTIL_RE.search(str(message or ""))
        explicit_ban_until = 0.0
        if match:
            raw = float(match.group(1))
            explicit_ban_until = raw / 1000.0 if raw >= 10_000_000_000 else raw

        with self._locked_state() as state:
            state["request_in_flight_until"] = 0.0
            state["used_weight_1m"] = used_1m
            state["used_weight"] = used
            if status == 418 or code == "-1003":
                fallback = retry_after or DEFAULT_418_COOLDOWN_SECONDS
                state["ban_until"] = max(explicit_ban_until, now + fallback)
                state["last_418_at"] = _now_iso(now)
                state["last_error_code"] = code or str(status)
                state["last_retry_after"] = retry_after
                state["public_read_healthy"] = False
                state["probe_in_flight_until"] = 0.0
            elif status == 429:
                state["ban_until"] = now + (retry_after or DEFAULT_429_COOLDOWN_SECONDS)
                state["last_error_code"] = code or "429"
                state["last_retry_after"] = retry_after
                state["public_read_healthy"] = False
                state["probe_in_flight_until"] = 0.0
            elif 200 <= status < 300:
                if health_probe:
                    state["ban_until"] = 0.0
                    state["public_read_healthy"] = True
                    state["probe_in_flight_until"] = 0.0
                state["last_error_code"] = ""

    def release_after_transport_error(self) -> None:
        with self._locked_state() as state:
            state["request_in_flight_until"] = 0.0


def _limiter_enabled() -> bool:
    explicit = os.environ.get("BINANCE_REST_LIMITER_ENABLED", "").strip().lower()
    if explicit:
        return explicit in {"1", "true", "yes", "on"}
    # Existing unit tests use mocked Binance URLs. They test parsing rather than
    # filesystem coordination; limiter behavior has its own isolated tests.
    return "PYTEST_CURRENT_TEST" not in os.environ


def run_binance_rest_call(
    call: Callable[[], T],
    *,
    url: str,
    weight: Optional[int] = None,
    health_probe: bool = False,
    limiter: Optional[BinanceRestLimiter] = None,
) -> T:
    """Execute one public Binance market-data call without HTTP retries."""
    parsed = urlparse(str(url))
    host = (parsed.hostname or "").lower()
    if (
        host not in _BINANCE_HOSTS
        or parsed.path not in _PUBLIC_MARKET_PATHS
        or (limiter is None and not _limiter_enabled())
    ):
        return call()
    active = limiter or BinanceRestLimiter()
    active.acquire(weight=weight or estimate_request_weight(url), health_probe=health_probe)
    try:
        response = call()
    except HTTPError as exc:
        body = exc.read()
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (TypeError, ValueError, UnicodeDecodeError):
            payload = {}
        active.observe(
            status_code=int(getattr(exc, "code", 0) or 0),
            headers=getattr(exc, "headers", None),
            error_code=payload.get("code") if isinstance(payload, dict) else None,
            message=str(payload.get("msg", "")) if isinstance(payload, dict) else "",
            health_probe=health_probe,
        )
        replacement = io.BytesIO(body)
        exc.fp = replacement
        exc.file = replacement
        exc.read = replacement.read
        exc.readline = replacement.readline
        raise
    except Exception:
        active.release_after_transport_error()
        raise
    response_status = int(
        getattr(response, "status", 0)
        or getattr(response, "status_code", 0)
        or 200
    )
    error_code: int | str | None = None
    message = ""
    if response_status >= 400 and callable(getattr(response, "json", None)):
        try:
            error_payload = response.json()
        except Exception:
            error_payload = {}
        if isinstance(error_payload, dict):
            error_code = error_payload.get("code")
            message = str(error_payload.get("msg", ""))
    active.observe(
        status_code=response_status,
        headers=getattr(response, "headers", None),
        error_code=error_code,
        message=message,
        health_probe=health_probe,
    )
    return response
