from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from email.message import Message
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from unittest.mock import patch

import pytest

from core.binance_rest_limiter import (
    BinanceRestBlocked,
    BinanceRestLimiter,
    estimate_request_weight,
    run_binance_rest_call,
)
from core.public_market_data import _http_json_with_retry


class Clock:
    def __init__(self, value: float = 1_700_000_000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value


class Response:
    def __init__(self, status: int = 200, headers: dict | None = None, payload: dict | None = None):
        self.status = status
        self.headers = headers or {}
        self._payload = payload or {}

    def json(self):
        return self._payload


def limiter(tmp_path: Path, clock: Clock, *, budget: int = 240) -> BinanceRestLimiter:
    return BinanceRestLimiter(tmp_path / "rate.json", clock=clock, safe_weight_budget=budget)


def test_200_normal_records_headers_and_clears_in_flight(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(
        status_code=200,
        headers={"X-MBX-USED-WEIGHT-1M": "17", "X-MBX-USED-WEIGHT": "9"},
    )
    state = guard.snapshot()
    assert state["request_in_flight_until"] == 0
    assert state["used_weight_1m"] == 17
    assert state["used_weight"] == 9


def test_429_enters_global_cooldown_and_respects_retry_after(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(status_code=429, headers={"Retry-After": "90"}, error_code=-1003)
    state = guard.snapshot()
    assert state["ban_until"] == pytest.approx(clock.value + 90)
    assert state["last_retry_after"] == 90
    with pytest.raises(BinanceRestBlocked, match="BINANCE_IP_BANNED"):
        guard.acquire(weight=1)


def test_418_persists_explicit_ban_until(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    future_ms = int((clock.value + 3_600) * 1000)
    guard.observe(
        status_code=418,
        headers={"Retry-After": "30"},
        error_code=-1003,
        message=f"IP banned until {future_ms}.",
    )
    state = guard.snapshot()
    assert state["ban_until"] == pytest.approx(clock.value + 3_600)
    assert state["last_418_at"]
    assert state["last_error_code"] == "-1003"


def test_minus_1003_without_418_still_persists_ban(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(status_code=400, error_code=-1003, message="too many requests")
    assert guard.snapshot()["ban_until"] == pytest.approx(clock.value + 300)


def test_restart_while_banned_makes_no_http_call(tmp_path: Path):
    clock = Clock()
    path = tmp_path / "rate.json"
    first = BinanceRestLimiter(path, clock=clock)
    first.acquire(weight=1)
    first.observe(status_code=418, headers={"Retry-After": "120"}, error_code=-1003)
    restarted = BinanceRestLimiter(path, clock=clock)
    calls = 0

    def network():
        nonlocal calls
        calls += 1
        return Response()

    with pytest.raises(BinanceRestBlocked, match="BINANCE_IP_BANNED"):
        run_binance_rest_call(
            network,
            url="https://fapi.binance.com/fapi/v1/time",
            limiter=restarted,
        )
    assert calls == 0


def test_ban_expiry_allows_exactly_one_health_probe(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(status_code=418, headers={"Retry-After": "10"}, error_code=-1003)
    clock.value += 11
    with pytest.raises(BinanceRestBlocked, match="RECOVERY_PROBE_REQUIRED"):
        guard.acquire(weight=1)
    guard.acquire(weight=1, health_probe=True)
    with pytest.raises(BinanceRestBlocked, match="RECOVERY_PROBE_IN_FLIGHT"):
        guard.acquire(weight=1, health_probe=True)


def test_successful_probe_marks_read_recovered(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(status_code=418, headers={"Retry-After": "1"}, error_code=-1003)
    clock.value += 2
    guard.acquire(weight=1, health_probe=True)
    guard.observe(status_code=200, health_probe=True)
    assert guard.snapshot()["public_read_healthy"] is True
    clock.value += 1
    guard.acquire(weight=1)


def test_failed_probe_restores_cooldown(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(status_code=418, headers={"Retry-After": "1"}, error_code=-1003)
    clock.value += 2
    guard.acquire(weight=1, health_probe=True)
    guard.observe(status_code=429, headers={"Retry-After": "60"}, error_code=-1003, health_probe=True)
    with pytest.raises(BinanceRestBlocked, match="BINANCE_IP_BANNED"):
        guard.acquire(weight=1)


@pytest.mark.parametrize("workers", [10, 50, 100])
def test_multiple_workers_allow_only_one_initial_in_flight(tmp_path: Path, workers: int):
    clock = Clock()
    path = tmp_path / "rate.json"

    def attempt(_: int) -> str:
        candidate = BinanceRestLimiter(path, clock=clock)
        try:
            candidate.acquire(weight=1)
            return "HTTP_ALLOWED"
        except BinanceRestBlocked:
            return "LOCAL_BLOCK"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(attempt, range(workers)))
    assert outcomes.count("HTTP_ALLOWED") == 1
    assert outcomes.count("LOCAL_BLOCK") == workers - 1


def test_local_weight_budget_blocks_without_http(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock, budget=5)
    guard.acquire(weight=5)
    guard.observe(status_code=200)
    with guard._locked_state() as state:
        state["next_request_at"] = 0
    with pytest.raises(BinanceRestBlocked, match="LOCAL_WEIGHT_BUDGET"):
        guard.acquire(weight=1)


def test_http_error_body_is_preserved_and_418_recorded(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    headers = Message()
    headers["Retry-After"] = "30"
    body = json.dumps({"code": -1003, "msg": "IP banned until 1700000100000"}).encode()
    error = HTTPError(
        "https://fapi.binance.com/fapi/v1/time", 418, "teapot", headers, io.BytesIO(body)
    )

    with pytest.raises(HTTPError) as captured:
        run_binance_rest_call(
            lambda: (_ for _ in ()).throw(error),
            url="https://fapi.binance.com/fapi/v1/time",
            limiter=guard,
        )
    assert captured.value.read() == body
    assert guard.snapshot()["last_error_code"] == "-1003"


def test_weight_estimates_cover_high_volume_paths():
    assert estimate_request_weight("https://fapi.binance.com/fapi/v1/klines?limit=99") == 1
    assert estimate_request_weight("https://fapi.binance.com/fapi/v1/klines?limit=500") == 5
    assert estimate_request_weight("https://fapi.binance.com/fapi/v1/klines?limit=1500") == 10
    assert estimate_request_weight("https://fapi.binance.com/fapi/v1/depth?limit=1000") == 20


def test_429_path_does_not_retry_http_and_next_call_is_locally_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("BINANCE_REST_LIMITER_ENABLED", "true")
    monkeypatch.setenv("BINANCE_REST_LIMIT_STATE_PATH", str(tmp_path / "shared.json"))
    headers = Message()
    headers["Retry-After"] = "60"
    body = json.dumps({"code": -1003, "msg": "Too many requests"}).encode()

    def rate_limited(*_args, **_kwargs):
        raise HTTPError(
            "https://fapi.binance.com/fapi/v1/time",
            429,
            "too many requests",
            headers,
            io.BytesIO(body),
        )

    with patch("core.public_market_data.urlopen", side_effect=rate_limited) as mocked:
        first = _http_json_with_retry(
            base_url="https://fapi.binance.com",
            path="/fapi/v1/time",
            query={},
            timeout_sec=1,
            retries_on_429=99,
        )
        second = _http_json_with_retry(
            base_url="https://fapi.binance.com",
            path="/fapi/v1/time",
            query={},
            timeout_sec=1,
            retries_on_429=99,
        )
    assert mocked.call_count == 1
    assert first["status_code"] == 429
    assert second["error"] == "BINANCE_IP_BANNED"


def test_private_endpoint_is_outside_public_market_limiter(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    calls = 0

    def private_call():
        nonlocal calls
        calls += 1
        return Response()

    run_binance_rest_call(
        private_call,
        url="https://fapi.binance.com/fapi/v2/account",
        limiter=guard,
    )
    assert calls == 1
    assert not guard.state_path.exists()


def test_state_and_lock_are_private_files(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    guard.observe(status_code=200)
    assert guard.state_path.stat().st_mode & 0o777 == 0o600
    assert guard.lock_path.stat().st_mode & 0o777 == 0o600


def test_state_is_shared_across_python_processes(tmp_path: Path):
    state_path = tmp_path / "cross-process.json"
    root = str(Path(__file__).resolve().parents[2])
    first = """
from shared.binance_rest_limiter import BinanceRestLimiter
g=BinanceRestLimiter(r'%s')
g.acquire(weight=1)
g.observe(status_code=418, headers={'Retry-After':'120'}, error_code=-1003)
""" % state_path
    second = """
from shared.binance_rest_limiter import BinanceRestBlocked, BinanceRestLimiter
g=BinanceRestLimiter(r'%s')
try:
    g.acquire(weight=1)
except BinanceRestBlocked as exc:
    print(exc.reason)
""" % state_path
    env = {**os.environ, "PYTHONPATH": root}
    subprocess.run([sys.executable, "-c", first], check=True, env=env)
    result = subprocess.run(
        [sys.executable, "-c", second], check=True, env=env, capture_output=True, text=True
    )
    assert result.stdout.strip() == "BINANCE_IP_BANNED"


def test_whole_server_mix_is_smoothed_under_240_weight_per_minute(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)

    def advance(seconds: float):
        clock.value += seconds

    urls = (
        ["https://fapi.binance.com/fapi/v1/klines?limit=1500"] * 166
        + ["https://fapi.binance.com/fapi/v1/klines?limit=500"] * 21
        + ["https://fapi.binance.com/fapi/v1/klines?limit=500"] * 25
        + ["https://fapi.binance.com/fapi/v1/klines?limit=500"]
        + ["https://fapi.binance.com/fapi/v1/fundingRate?limit=1000"] * 24
    )
    for url in urls:
        run_binance_rest_call(
            lambda: Response(200), url=url, limiter=guard, sleeper=advance
        )
    state = guard.snapshot()
    assert state["total_requests"] == len(urls)
    assert state["maximum_observed_1m_weight"] <= 240
    assert state["wait_count"] > 0


def test_in_flight_contention_rechecks_before_full_crash_lease(tmp_path: Path):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    guard.acquire(weight=1)
    sleeps = []

    def release_after_short_wait(seconds: float):
        sleeps.append(seconds)
        clock.value += seconds
        guard.observe(status_code=200)

    guard.acquire_with_pacing(weight=1, sleeper=release_after_short_wait)
    assert sleeps == [pytest.approx(0.1), pytest.approx(0.15)]


@pytest.mark.parametrize("status", [429, 418])
def test_rate_limit_at_request_n_stops_all_later_components(tmp_path: Path, status: int):
    clock = Clock()
    guard = limiter(tmp_path, clock)
    network_calls = 0

    def advance(seconds: float):
        clock.value += seconds

    def request():
        nonlocal network_calls
        network_calls += 1
        if network_calls == 8:
            return Response(status, {"Retry-After": "60"}, {"code": -1003, "msg": "limited"})
        return Response(200)

    for _component in range(5):
        for _request in range(20):
            try:
                run_binance_rest_call(
                    request,
                    url="https://fapi.binance.com/fapi/v1/klines?limit=500",
                    limiter=guard,
                    sleeper=advance,
                )
            except BinanceRestBlocked:
                pass
    assert network_calls == 8
    state = guard.snapshot()
    assert state["error_1003_count"] == 1
    assert state[f"status_{status}_count"] == 1
