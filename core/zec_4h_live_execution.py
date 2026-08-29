"""Guarded USD-M execution adapter and orchestration for ``zec_4h_live_v1``.

The real adapter is inert unless constructed with ``live_enabled=True``.  Unit
tests use protocol-compatible fakes; this module never reads credentials from
disk and never enables itself.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional, Protocol

from core.binance_http import (
    build_public_request,
    build_signed_request,
    send_binance_request,
)
from core.order_normalizer import normalize_order_params
from core.zec_4h_live import (
    ACCOUNT_MODE,
    API_MODE,
    APPROVED_LIVE_SAFETY_DEVIATIONS,
    LiveAction,
    LiveExecutionLedger,
    FIXED_LEVERAGE,
    LIVE_CAPITAL_CAP_USDT,
    TARGET_INITIAL_NOTIONAL_USDT,
    SIZING_BASE_USDT,
    STRATEGY_ID,
    STARTING_EQUITY,
    SYMBOL,
    TIMEFRAME,
    StrategyDecision,
    StrategyPhase,
    StrategyState,
    Zec4hStrategy,
    build_client_order_id,
    build_signal_key,
    safe_initial_notional,
)


ORDER_STATUSES = {
    "NEW",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCELED",
    "REJECTED",
    "EXPIRED",
    "EXPIRED_IN_MATCH",
}
TERMINAL_ORDER_STATUSES = {"FILLED", "CANCELED", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH"}
TERMINAL_FAILURE_STATUSES = {"CANCELED", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH"}
UNKNOWN_STATUS = "UNKNOWN_RECONCILIATION_REQUIRED"
STALE_RISK_INCREASE_STATUS = "STALE_RISK_INCREASE_BLOCKED"
RISK_INCREASE_ACTIONS = {LiveAction.OPEN.value, LiveAction.ADD_50.value}
RISK_REDUCTION_ACTIONS = {
    LiveAction.REDUCE_50.value,
    LiveAction.STOP_CLOSE.value,
    LiveAction.TAKE_PROFIT_CLOSE.value,
    LiveAction.HARD_STOP_CLOSE.value,
}


class ExecutionAdapter(Protocol):
    def get_account(self) -> dict[str, Any]: ...
    def get_balance(self) -> list[dict[str, Any]]: ...
    def get_position(self, symbol: str = SYMBOL) -> dict[str, Any]: ...
    def get_open_orders(self, symbol: str = SYMBOL) -> list[dict[str, Any]]: ...
    def get_exchange_info(self) -> dict[str, Any]: ...
    def get_server_time(self) -> dict[str, Any]: ...
    def get_position_mode(self) -> dict[str, Any]: ...
    def get_api_restrictions(self) -> dict[str, Any]: ...
    def get_leverage_brackets(self, symbol: str = SYMBOL) -> Any: ...
    def get_symbol_config(self, symbol: str = SYMBOL) -> dict[str, Any]: ...
    def set_leverage(self, leverage: int, symbol: str = SYMBOL) -> dict[str, Any]: ...
    def submit_market_order(
        self,
        *,
        side: str,
        quantity: float,
        client_order_id: str,
        reduce_only: bool,
        position_side: str = "BOTH",
        symbol: str = SYMBOL,
    ) -> dict[str, Any]: ...
    def query_order(
        self,
        *,
        client_order_id: str,
        exchange_order_id: str = "",
        symbol: str = SYMBOL,
    ) -> Optional[dict[str, Any]]: ...
    def cancel_order(
        self,
        *,
        client_order_id: str = "",
        exchange_order_id: str = "",
        symbol: str = SYMBOL,
    ) -> dict[str, Any]: ...
    def get_fills(self, symbol: str = SYMBOL, order_id: str = "") -> list[dict[str, Any]]: ...
    def get_income(self, symbol: str = SYMBOL, income_type: str = "FUNDING_FEE") -> list[dict[str, Any]]: ...


class BinanceUsdMExecutionAdapter:
    """HMAC Portfolio Margin UM adapter for ZECUSDT execution and audit."""

    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        live_enabled: bool = False,
        transport: Any = None,
        timestamp_ms: Optional[int] = None,
    ):
        self._api_key = str(api_key or "").strip()
        self._api_secret = str(api_secret or "").strip()
        self._live_enabled = bool(live_enabled)
        self._transport = transport
        self._timestamp_ms = timestamp_ms

    def _signed(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        *,
        market_type: str = "portfolio_margin",
    ) -> Any:
        if not self._api_key or not self._api_secret:
            raise RuntimeError("BINANCE_LIVE_CREDENTIALS_MISSING")
        request = build_signed_request(
            method=method,
            path=path,
            environment="live",
            market_type=market_type,
            api_key=self._api_key,
            api_secret=self._api_secret,
            params=params or {},
            timestamp_ms=self._timestamp_ms,
        )
        result = send_binance_request(request, transport=self._transport)
        if result.get("ok") is not True:
            code = (
                result.get("binance_code") or result.get("exchange_code")
                or result.get("error_code") or result.get("error") or "UNKNOWN"
            )
            raise RuntimeError(f"BINANCE_API_ERROR:{code}")
        return result.get("data", result.get("response_json", result.get("response")))

    def _public(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        request = build_public_request(
            method="GET",
            path=path,
            environment="live",
            market_type="futures",
            params=params or {},
        )
        result = send_binance_request(request, transport=self._transport)
        if result.get("ok") is not True:
            raise RuntimeError("BINANCE_PUBLIC_API_ERROR")
        return result.get("data", result.get("response_json", result.get("response")))

    def _assert_live_write(self) -> None:
        if not self._live_enabled:
            raise RuntimeError("ZEC_4H_LIVE_WRITE_DISABLED")

    def get_account(self) -> dict[str, Any]:
        value = self._signed("GET", "/papi/v1/um/account")
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_ACCOUNT_RESPONSE")
        return value

    def get_balance(self) -> list[dict[str, Any]]:
        value = self._signed("GET", "/papi/v1/balance")
        if not isinstance(value, list):
            raise RuntimeError("MALFORMED_BALANCE_RESPONSE")
        return [dict(item) for item in value if isinstance(item, dict)]

    def get_position(self, symbol: str = SYMBOL) -> dict[str, Any]:
        value = self._signed("GET", "/papi/v1/um/positionRisk", {"symbol": symbol})
        if isinstance(value, list):
            matches = [item for item in value if isinstance(item, dict) and item.get("symbol") == symbol]
            short_positions = [
                item for item in matches
                if str(item.get("positionSide", "")).upper() == "SHORT"
                and abs(float(item.get("positionAmt", 0.0) or 0.0)) > 1e-12
            ]
            if short_positions:
                raise RuntimeError("SHORT_POSITION_FORBIDDEN")
            long_positions = [
                item for item in matches
                if str(item.get("positionSide", "")).upper() == "LONG"
            ]
            both_positions = [
                item for item in matches
                if str(item.get("positionSide", "BOTH")).upper() == "BOTH"
            ]
            if len(long_positions) == 1:
                return dict(long_positions[0])
            if len(both_positions) == 1:
                return dict(both_positions[0])
            if not matches and len(value) == 0:
                # PAPI omits symbols that have neither a position nor an open
                # order. Preserve the executor's explicit zero-position shape.
                return {"symbol": symbol, "positionAmt": "0", "positionSide": "BOTH"}
        if isinstance(value, dict) and value.get("symbol") == symbol:
            return dict(value)
        raise RuntimeError("MALFORMED_POSITION_RESPONSE")

    def get_open_orders(self, symbol: str = SYMBOL) -> list[dict[str, Any]]:
        value = self._signed("GET", "/papi/v1/um/openOrders", {"symbol": symbol})
        if not isinstance(value, list):
            raise RuntimeError("MALFORMED_OPEN_ORDERS_RESPONSE")
        return [dict(item) for item in value if isinstance(item, dict)]

    def get_exchange_info(self) -> dict[str, Any]:
        value = self._public("/fapi/v1/exchangeInfo")
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_EXCHANGE_INFO_RESPONSE")
        return value

    def get_server_time(self) -> dict[str, Any]:
        value = self._public("/fapi/v1/time")
        if not isinstance(value, dict) or "serverTime" not in value:
            raise RuntimeError("MALFORMED_SERVER_TIME_RESPONSE")
        return value

    def get_position_mode(self) -> dict[str, Any]:
        value = self._signed("GET", "/papi/v1/um/positionSide/dual")
        if not isinstance(value, dict) or "dualSidePosition" not in value:
            raise RuntimeError("MALFORMED_POSITION_MODE_RESPONSE")
        return value

    def get_api_restrictions(self) -> dict[str, Any]:
        value = self._signed(
            "GET",
            "/sapi/v1/account/apiRestrictions",
            market_type="spot",
        )
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_API_RESTRICTIONS_RESPONSE")
        return value

    def get_leverage_brackets(self, symbol: str = SYMBOL) -> Any:
        value = self._signed("GET", "/papi/v1/um/leverageBracket", {"symbol": symbol})
        if not isinstance(value, (dict, list)):
            raise RuntimeError("MALFORMED_LEVERAGE_BRACKET_RESPONSE")
        return value

    def get_symbol_config(self, symbol: str = SYMBOL) -> dict[str, Any]:
        value = self._signed("GET", "/papi/v1/um/symbolConfig", {"symbol": symbol})
        rows = value if isinstance(value, list) else [value]
        matches = [row for row in rows if isinstance(row, dict) and row.get("symbol") == symbol]
        if len(matches) != 1:
            raise RuntimeError("MALFORMED_SYMBOL_CONFIG_RESPONSE")
        return dict(matches[0])

    def set_leverage(self, leverage: int, symbol: str = SYMBOL) -> dict[str, Any]:
        self._assert_live_write()
        value = self._signed("POST", "/papi/v1/um/leverage", {"symbol": symbol, "leverage": int(leverage)})
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_LEVERAGE_RESPONSE")
        return value

    def submit_market_order(
        self,
        *,
        side: str,
        quantity: float,
        client_order_id: str,
        reduce_only: bool,
        position_side: str = "BOTH",
        symbol: str = SYMBOL,
    ) -> dict[str, Any]:
        self._assert_live_write()
        normalized_position_side = str(position_side).upper()
        if normalized_position_side not in {"BOTH", "LONG"}:
            raise ValueError("LONG_ONLY_POSITION_SIDE_REQUIRED")
        params = {
            "symbol": symbol,
            "side": str(side).upper(),
            "type": "MARKET",
            "quantity": _decimal_text(quantity),
            "newClientOrderId": str(client_order_id)[:35],
            "newOrderRespType": "RESULT",
            "positionSide": normalized_position_side,
        }
        if normalized_position_side == "BOTH":
            params["reduceOnly"] = bool(reduce_only)
        elif reduce_only and str(side).upper() != "SELL":
            raise ValueError("LONG_HEDGE_REDUCTION_MUST_SELL")
        value = self._signed("POST", "/papi/v1/um/order", params)
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_ORDER_RESPONSE")
        return value

    def query_order(
        self,
        *,
        client_order_id: str,
        exchange_order_id: str = "",
        symbol: str = SYMBOL,
    ) -> Optional[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": symbol}
        if exchange_order_id:
            params["orderId"] = exchange_order_id
        else:
            params["origClientOrderId"] = client_order_id
        try:
            value = self._signed("GET", "/papi/v1/um/order", params)
        except RuntimeError as exc:
            if "-2013" in str(exc):
                return None
            raise
        if value is None:
            return None
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_QUERY_ORDER_RESPONSE")
        return value

    def cancel_order(
        self,
        *,
        client_order_id: str = "",
        exchange_order_id: str = "",
        symbol: str = SYMBOL,
    ) -> dict[str, Any]:
        self._assert_live_write()
        params: dict[str, Any] = {"symbol": symbol}
        if exchange_order_id:
            params["orderId"] = exchange_order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("order identity required")
        value = self._signed("DELETE", "/papi/v1/um/order", params)
        if not isinstance(value, dict):
            raise RuntimeError("MALFORMED_CANCEL_RESPONSE")
        return value

    def get_fills(self, symbol: str = SYMBOL, order_id: str = "") -> list[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": symbol, "limit": 1000}
        if order_id:
            params["orderId"] = order_id
        value = self._signed("GET", "/papi/v1/um/userTrades", params)
        if not isinstance(value, list):
            raise RuntimeError("MALFORMED_FILLS_RESPONSE")
        return [dict(item) for item in value if isinstance(item, dict)]

    def get_income(self, symbol: str = SYMBOL, income_type: str = "FUNDING_FEE") -> list[dict[str, Any]]:
        value = self._signed(
            "GET",
            "/papi/v1/um/income",
            {"symbol": symbol, "incomeType": income_type, "limit": 1000},
        )
        if not isinstance(value, list):
            raise RuntimeError("MALFORMED_INCOME_RESPONSE")
        return [dict(item) for item in value if isinstance(item, dict)]


def _decimal_text(value: Any) -> str:
    return format(Decimal(str(value)).normalize(), "f")


def position_quantity(position: dict[str, Any]) -> float:
    return float(position.get("positionAmt", position.get("quantity", 0.0)) or 0.0)


def account_equity(account: dict[str, Any]) -> float:
    assets = [row for row in account.get("assets", []) if isinstance(row, dict)]
    usdt = [row for row in assets if str(row.get("asset", "")).upper() == "USDT"]
    if len(usdt) == 1:
        row = usdt[0]
        wallet = float(row.get("crossWalletBalance", row.get("walletBalance", 0.0)) or 0.0)
        unrealized = float(row.get("crossUnPnl", row.get("unrealizedProfit", 0.0)) or 0.0)
        return wallet + unrealized
    if "totalMarginBalance" in account:
        return float(account.get("totalMarginBalance") or 0.0)
    wallet = float(account.get("totalWalletBalance", account.get("walletBalance", 0.0)) or 0.0)
    unrealized = float(account.get("totalUnrealizedProfit", account.get("unrealizedProfit", 0.0)) or 0.0)
    return wallet + unrealized


def usdt_available_balance(rows: list[dict[str, Any]]) -> float:
    matches = [row for row in rows if str(row.get("asset", "")).upper() == "USDT"]
    if len(matches) != 1:
        raise ValueError("USDT balance unavailable")
    row = matches[0]
    return float(
        row.get(
            "availableBalance",
            row.get("crossMarginFree", row.get("balance", 0.0)),
        )
        or 0.0
    )


def strategy_equity_from_evidence(
    records: list[dict[str, Any]],
    position: dict[str, Any],
) -> float:
    """Exclude deposits or unrelated account funds from strategy allocation."""
    latest: dict[str, dict[str, Any]] = {}
    for row in records:
        if row.get("signal_key"):
            latest[str(row["signal_key"])] = row
    fills = [row for row in latest.values() if row.get("status") == "FILLED"]
    funding = [row for row in latest.values() if row.get("status") == "ACCOUNT_INCOME"]
    realized = sum(float(row.get("realized_pnl", 0.0) or 0.0) for row in fills)
    fees = sum(float(row.get("fee", 0.0) or 0.0) for row in fills)
    funding_total = sum(float(row.get("funding", 0.0) or 0.0) for row in funding)
    unrealized = float(
        position.get("unRealizedProfit", position.get("unrealizedProfit", 0.0)) or 0.0
    )
    return STARTING_EQUITY + realized - fees + funding_total + unrealized


def verify_dedicated_account_boundary(
    *,
    exchange_equity: float,
    strategy_equity: float,
    tolerance: float = 0.50,
) -> dict[str, Any]:
    difference = float(exchange_equity) - float(strategy_equity)
    return {
        "ok": abs(difference) <= tolerance,
        "difference": difference,
        "reason": "" if abs(difference) <= tolerance else "EXTERNAL_ACCOUNT_EQUITY_DETECTED",
    }


def extract_symbol_rules(exchange_info: dict[str, Any], symbol: str = SYMBOL) -> dict[str, Any]:
    symbols = [item for item in exchange_info.get("symbols", []) if isinstance(item, dict)]
    matches = [item for item in symbols if item.get("symbol") == symbol]
    if len(matches) != 1:
        raise ValueError("ZECUSDT exchange rules unavailable")
    row = matches[0]
    filters = {item.get("filterType"): item for item in row.get("filters", []) if isinstance(item, dict)}
    lot = filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE") or {}
    notional = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL") or {}
    price_filter = filters.get("PRICE_FILTER") or {}
    return {
        "symbol": symbol,
        "status": row.get("status"),
        "contract_type": row.get("contractType"),
        "price_precision": int(row.get("pricePrecision", -1)),
        "qty_precision": int(row.get("quantityPrecision", -1)),
        "tick_size": float(price_filter.get("tickSize", 0.0) or 0.0),
        "step_size": float(lot.get("stepSize", 0.0) or 0.0),
        "min_qty": float(lot.get("minQty", 0.0) or 0.0),
        "min_notional": float(notional.get("notional", notional.get("minNotional", 0.0)) or 0.0),
    }


def fixed_leverage_allowed(
    payload: Any,
    *,
    symbol: str = SYMBOL,
    leverage: int = FIXED_LEVERAGE,
    sizing_base_usdt: float = SIZING_BASE_USDT,
) -> bool:
    """Return whether the account bracket permits exactly the configured 50x."""
    rows = payload if isinstance(payload, list) else [payload]
    matches = [row for row in rows if isinstance(row, dict) and row.get("symbol") == symbol]
    if len(matches) != 1 or sizing_base_usdt <= 0:
        raise ValueError("LEVERAGE_BRACKET_UNAVAILABLE")
    bracket_payload = matches[0]
    brackets = [row for row in bracket_payload.get("brackets", []) if isinstance(row, dict)]
    notional_coefficient = float(bracket_payload.get("notionalCoef", 1.0) or 1.0)
    if leverage <= 0 or notional_coefficient <= 0:
        raise ValueError("INVALID_LEVERAGE_BRACKET")
    notional = sizing_base_usdt * leverage
    for bracket in brackets:
        floor = float(bracket.get("notionalFloor", 0.0) or 0.0) * notional_coefficient
        cap = float(bracket.get("notionalCap", 0.0) or 0.0) * notional_coefficient
        bracket_leverage = int(float(bracket.get("initialLeverage", 0) or 0))
        if floor <= notional and (cap <= 0 or notional < cap):
            return leverage <= bracket_leverage
    raise ValueError("NO_LEVERAGE_BRACKET_FOR_FIXED_NOTIONAL")


def run_portfolio_margin_read_only_preflight(
    adapter: ExecutionAdapter,
) -> dict[str, Any]:
    """Authenticate the Unified Account via PAPI without any write request."""
    checks: dict[str, Any] = {
        "papi_authentication": False,
        "portfolio_margin_access": False,
        "trading_permission": False,
        "withdraw_permission": "UNKNOWN",
        "zecusdt_available": False,
        "real_order": False,
        "live_enabled": False,
    }
    try:
        account = adapter.get_account()
        checks["papi_authentication"] = True
        checks["portfolio_margin_access"] = True
        checks["account_read"] = isinstance(account, dict)

        balances = adapter.get_balance()
        checks["balance_read"] = isinstance(balances, list)
        position = adapter.get_position()
        checks["position_read"] = str(position.get("symbol", "")) == SYMBOL
        open_orders = adapter.get_open_orders()
        checks["open_orders_read"] = isinstance(open_orders, list)

        symbol_config = adapter.get_symbol_config()
        rules = extract_symbol_rules(adapter.get_exchange_info())
        checks["zecusdt_available"] = (
            str(symbol_config.get("symbol", "")) == SYMBOL
            and rules.get("status") == "TRADING"
            and rules.get("contract_type") == "PERPETUAL"
        )
        checks["zecusdt_position_qty"] = position_quantity(position)
        checks["zecusdt_open_order_count"] = len(open_orders)

        restrictions = adapter.get_api_restrictions()
        checks["trading_permission"] = _to_bool(
            restrictions.get("enablePortfolioMarginTrading")
        )
        withdrawals_enabled = _to_bool(restrictions.get("enableWithdrawals"))
        checks["withdraw_permission"] = "ON" if withdrawals_enabled else "OFF"
    except Exception as exc:
        checks["error"] = exc.__class__.__name__
        checks["preflight_pass"] = False
        return checks

    checks["preflight_pass"] = all([
        checks["papi_authentication"],
        checks["portfolio_margin_access"],
        checks["trading_permission"],
        checks["withdraw_permission"] == "OFF",
        checks["zecusdt_available"],
        checks.get("balance_read") is True,
        checks.get("position_read") is True,
        checks.get("open_orders_read") is True,
    ])
    return checks


def run_live_preflight(
    adapter: ExecutionAdapter,
    *,
    expected_budget: float = 50.0,
    withdrawal_disabled_verified: bool = False,
    maximum_clock_skew_ms: int = 1000,
    local_time_ms: Optional[int] = None,
) -> dict[str, Any]:
    """Authenticated PAPI no-order preflight for the fixed software allocation."""
    checks: dict[str, Any] = {}
    try:
        rules = extract_symbol_rules(adapter.get_exchange_info())
        checks["symbol_tradeable"] = rules["status"] == "TRADING" and rules["contract_type"] == "PERPETUAL"
        checks["symbol_rules"] = rules
        server_time = int(adapter.get_server_time().get("serverTime", 0))
        local_ms = int(local_time_ms if local_time_ms is not None else datetime.now(timezone.utc).timestamp() * 1000)
        checks["clock_skew_ms"] = abs(local_ms - server_time)
        checks["clock_ok"] = checks["clock_skew_ms"] <= maximum_clock_skew_ms
        account = adapter.get_account()
        checks["api_authentication"] = True
        checks["papi_authentication"] = True
        checks["portfolio_margin_access"] = True
        checks["api_read"] = True
        restrictions = adapter.get_api_restrictions()
        checks["trading_permission"] = _to_bool(
            restrictions.get("enablePortfolioMarginTrading")
        )
        checks["api_trade"] = checks["trading_permission"]
        checks["withdrawal_disabled_verified"] = not _to_bool(restrictions.get("enableWithdrawals"))
        checks["withdraw_permission"] = (
            "OFF" if checks["withdrawal_disabled_verified"] else "ON"
        )
        checks["ip_restricted"] = _to_bool(restrictions.get("ipRestrict"))
        checks["account_equity"] = account_equity(account)
        checks["available_balance"] = usdt_available_balance(adapter.get_balance())
        checks["available_buffer_ok"] = checks["available_balance"] >= SIZING_BASE_USDT
        checks["strategy_budget_ok"] = expected_budget == LIVE_CAPITAL_CAP_USDT
        checks["account_mode"] = ACCOUNT_MODE
        checks["api_mode"] = API_MODE
        checks["capital_cap_usdt"] = LIVE_CAPITAL_CAP_USDT
        checks["sizing_base_usdt"] = SIZING_BASE_USDT
        checks["target_initial_notional_usdt"] = TARGET_INITIAL_NOTIONAL_USDT
        position = adapter.get_position()
        symbol_config = adapter.get_symbol_config()
        checks["position_zero"] = abs(position_quantity(position)) <= 1e-12
        checks["fixed_leverage"] = FIXED_LEVERAGE
        checks["zecusdt_50x_allowed"] = fixed_leverage_allowed(adapter.get_leverage_brackets())
        checks["account_leverage"] = int(float(symbol_config.get("leverage", 0) or 0))
        checks["leverage_fixed_50x"] = checks["account_leverage"] == FIXED_LEVERAGE
        dual_side = _dual_side_mode(adapter.get_position_mode())
        checks["position_mode"] = "HEDGE" if dual_side else "ONE_WAY"
        checks["long_only_position_side"] = "LONG" if dual_side else "BOTH"
        checks["position_mode_supported"] = True
        checks["open_orders_zero"] = len(adapter.get_open_orders()) == 0
        if withdrawal_disabled_verified:
            checks["withdrawal_disabled_verified"] = checks["withdrawal_disabled_verified"] is True
    except Exception as exc:
        checks["error"] = exc.__class__.__name__
        checks.setdefault("api_authentication", False)
        checks.setdefault("papi_authentication", False)
        checks.setdefault("portfolio_margin_access", False)
        checks.setdefault("trading_permission", False)
        checks.setdefault("withdraw_permission", "UNKNOWN")
        checks["preflight_pass"] = False
        return checks
    required = [
        "symbol_tradeable", "clock_ok", "api_read", "api_trade", "strategy_budget_ok", "available_buffer_ok",
        "position_zero", "zecusdt_50x_allowed", "leverage_fixed_50x", "position_mode_supported", "open_orders_zero",
        "withdrawal_disabled_verified", "ip_restricted",
    ]
    checks["preflight_pass"] = all(checks.get(key) is True for key in required)
    return checks


def reconcile_startup(
    state: StrategyState,
    ledger: LiveExecutionLedger,
    adapter: ExecutionAdapter,
    *,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Fail closed when local ledger/state and exchange truth disagree."""
    position = adapter.get_position()
    exchange_qty = position_quantity(position)
    open_orders = adapter.get_open_orders()
    if exchange_qty < -tolerance:
        return {"ok": False, "reason": "SHORT_POSITION_FORBIDDEN", "exchange_qty": exchange_qty}

    records = ledger.read()
    latest: dict[str, dict[str, Any]] = {}
    for row in records:
        if row.get("signal_key"):
            latest[str(row["signal_key"])] = row
    pending = [row for row in latest.values() if row.get("status") in {"SIGNAL_CONFIRMED", "SUBMITTING", "NEW", "PARTIALLY_FILLED", UNKNOWN_STATUS}]
    known_clients = {str(row.get("client_order_id", "")) for row in pending}
    unknown_exchange_orders = [
        item for item in open_orders
        if str(item.get("clientOrderId", item.get("client_order_id", ""))) not in known_clients
    ]
    if unknown_exchange_orders:
        return {"ok": False, "reason": "UNRECOGNIZED_EXCHANGE_OPEN_ORDER"}

    expected_qty = float(state.actual_position_qty)
    if abs(exchange_qty - expected_qty) > tolerance and not pending:
        return {
            "ok": False,
            "reason": "LOCAL_EXCHANGE_POSITION_MISMATCH",
            "local_qty": expected_qty,
            "exchange_qty": exchange_qty,
        }
    if state.phase in {StrategyPhase.FLAT.value, StrategyPhase.TARGET_REACHED_PAUSED.value} and exchange_qty > tolerance and not pending:
        return {"ok": False, "reason": "EXCHANGE_POSITION_WHILE_LOCAL_FLAT"}
    if exchange_qty > tolerance:
        if state.entry_low is None or float(state.entry_low) <= 0:
            return {"ok": False, "reason": "STOP_GUARD_PRICE_UNAVAILABLE"}
        if (
            not state.take_profit_active
            or state.take_profit_price is None
            or state.initial_entry_price is None
            or state.initial_stop_price is None
            or float(state.take_profit_price) <= float(state.initial_entry_price)
        ):
            return {"ok": False, "reason": "TAKE_PROFIT_GUARD_UNAVAILABLE"}
        state.stop_guard_price = float(state.entry_low)
        state.stop_guard_active = True
    else:
        state.stop_guard_price = None
        state.stop_guard_active = False
    return {
        "ok": True,
        "exchange_qty": exchange_qty,
        "open_order_count": len(open_orders),
        "pending_local_order_count": len(pending),
        "position": position,
        "open_orders": open_orders,
    }


def _decision_from_ledger_record(row: dict[str, Any]) -> StrategyDecision:
    return StrategyDecision(
        action=str(row.get("action", "")),
        signal_key=str(row.get("signal_key", "")),
        client_order_id=str(row.get("client_order_id", "")),
        bar_close_time=str(row.get("bar_close_time", "")),
        signal_price=float(row.get("signal_price", 0.0) or 0.0),
        entry_low=(float(row["entry_low"]) if row.get("entry_low") is not None else None),
        reason=str(row.get("reason", "RECOVERED_FROM_LEDGER")),
    )


def _partial_terminal_safety_decision(
    original: StrategyDecision,
    *,
    status: str,
) -> StrategyDecision:
    action = LiveAction.HARD_STOP_CLOSE.value
    signal_key = f"{original.signal_key}:RESIDUAL:{status}"
    return StrategyDecision(
        action=action,
        signal_key=signal_key,
        client_order_id=build_client_order_id(signal_key, action, original.bar_close_time),
        bar_close_time=original.bar_close_time,
        signal_price=original.signal_price,
        entry_low=None,
        reason=f"TERMINAL_ORDER_{status}_SAFETY_EXIT",
        diagnostics={"terminal_source_signal_key": original.signal_key},
    )


def _arm_terminal_safety_exit(
    state: StrategyState,
    decision: StrategyDecision,
    *,
    status: str,
    exchange_qty: float,
    partial_fill: bool,
) -> None:
    qty = float(exchange_qty)
    state.phase = StrategyPhase.HARD_STOP.value
    state.pending_action = ""
    state.pending_decision = {}
    if qty > 1e-12:
        state.hard_stop_reason = (
            f"ORDER_{status}_WITH_PARTIAL_FILL" if partial_fill else f"ORDER_{status}_WITH_OPEN_POSITION"
        )
        state.actual_position_qty = qty
        state.full_position_qty = max(state.full_position_qty, qty)
        close_decision = _partial_terminal_safety_decision(decision, status=status)
        state.pending_action = LiveAction.HARD_STOP_CLOSE.value
        state.recovery_status = (
            "PARTIAL_TERMINAL_SAFETY_EXIT_REQUIRED" if partial_fill else "TERMINAL_SAFETY_EXIT_REQUIRED"
        )
        state.recovery_decision = asdict(close_decision)
    elif qty < -1e-12:
        state.hard_stop_reason = f"ORDER_{status}_POSITION_DIRECTION_AMBIGUOUS"
        state.recovery_status = "TERMINAL_POSITION_DIRECTION_AMBIGUOUS"
        state.recovery_decision = {}
    else:
        state.hard_stop_reason = f"ORDER_{status}"
        state.actual_position_qty = 0.0
        state.recovery_status = ""
        state.recovery_decision = {}


def _apply_partial_terminal_transition(
    state: StrategyState,
    decision: StrategyDecision,
    *,
    status: str,
    filled_qty: float,
) -> None:
    if decision.signal_key in state.applied_fill_signal_keys:
        return
    qty = max(0.0, float(filled_qty))
    if decision.action in {LiveAction.OPEN.value, LiveAction.ADD_50.value}:
        state.actual_position_qty += qty
        state.full_position_qty = max(state.full_position_qty, state.actual_position_qty)
        if decision.action == LiveAction.OPEN.value and decision.entry_low is not None:
            state.entry_low = float(decision.entry_low)
    else:
        state.actual_position_qty = max(0.0, state.actual_position_qty - qty)
    state.applied_fill_signal_keys.append(decision.signal_key)
    state.pending_action = ""
    state.pending_decision = {}
    state.phase = StrategyPhase.HARD_STOP.value
    state.hard_stop_reason = f"ORDER_{status}_WITH_PARTIAL_FILL"
    if state.actual_position_qty > 1e-12:
        close_decision = _partial_terminal_safety_decision(decision, status=status)
        state.pending_action = LiveAction.HARD_STOP_CLOSE.value
        state.recovery_status = "PARTIAL_TERMINAL_SAFETY_EXIT_REQUIRED"
        state.recovery_decision = asdict(close_decision)
    else:
        state.recovery_status = ""
        state.recovery_decision = {}


def recover_unapplied_filled_transitions(
    state: StrategyState,
    ledger: LiveExecutionLedger,
    adapter: ExecutionAdapter,
    *,
    tolerance: float = 1e-9,
) -> dict[str, Any]:
    """Apply ledgered exchange fills exactly once before startup reconciliation."""
    latest: dict[str, dict[str, Any]] = {}
    for row in ledger.read():
        signal_key = str(row.get("signal_key", ""))
        if signal_key:
            latest[signal_key] = dict(row)

    recovered_terminal = 0
    # Zero-fill terminal orders also need crash-safe flattening if the account
    # still carries a long position.  Inspect both normal pending decisions and
    # persisted safety/recovery decisions before candidate fill replay.
    for payload_name in ("pending_decision", "recovery_decision"):
        payload = getattr(state, payload_name)
        signal_key = str(payload.get("signal_key", "")) if payload else ""
        terminal = latest.get(signal_key) if signal_key else None
        if terminal is None:
            continue
        status = str(terminal.get("status", "")).upper()
        filled = float(terminal.get("filled_qty", 0.0) or 0.0)
        if status not in TERMINAL_FAILURE_STATUSES or filled > 0:
            continue
        decision = _decision_from_ledger_record(terminal)
        exchange_qty = position_quantity(adapter.get_position())
        _arm_terminal_safety_exit(
            state,
            decision,
            status=status,
            exchange_qty=exchange_qty,
            partial_fill=False,
        )
        recovered_terminal += 1
        # The new recovery decision replaces the settled failed one.  Do not
        # allow the same failed payload to participate in candidate replay.
        break

    # Only decisions persisted as in-flight before submission are eligible.
    # Existing ledgers predate ``applied_fill_signal_keys``; scanning every
    # historical FILLED row on upgrade would double-apply settled exposure.
    recoverable_signal_keys = {
        str(payload.get("signal_key", ""))
        for payload in (state.pending_decision, state.recovery_decision)
        if payload
    }
    recoverable_signal_keys.discard("")
    candidates = [
        row for row in latest.values()
        if str(row.get("signal_key", "")) in recoverable_signal_keys
        and str(row.get("signal_key", "")) not in state.applied_fill_signal_keys
        and float(row.get("filled_qty", 0.0) or 0.0) > 0
        and (
            str(row.get("status", "")).upper() == "FILLED"
            or str(row.get("status", "")).upper() in {"CANCELED", "EXPIRED", "EXPIRED_IN_MATCH", "REJECTED"}
        )
    ]
    if not candidates:
        return {"ok": True, "recovered": recovered_terminal}
    candidates.sort(key=lambda row: str(row.get("recorded_at", "")))
    projected = StrategyState.from_dict(state.to_dict())
    for row in candidates:
        decision = _decision_from_ledger_record(row)
        status = str(row.get("status", "")).upper()
        filled_qty = float(row.get("filled_qty", 0.0) or 0.0)
        if status == "FILLED":
            Zec4hStrategy.apply_filled_action(
                projected,
                decision,
                filled_qty=filled_qty,
                average_fill_price=float(row.get("average_fill_price", 0.0) or 0.0),
            )
        else:
            _apply_partial_terminal_transition(
                projected,
                decision,
                status=status,
                filled_qty=filled_qty,
            )
    exchange_qty = position_quantity(adapter.get_position())
    if abs(projected.actual_position_qty - exchange_qty) > tolerance:
        return {
            "ok": False,
            "reason": "FILLED_LEDGER_EXCHANGE_MISMATCH",
            "projected_qty": projected.actual_position_qty,
            "exchange_qty": exchange_qty,
        }
    for name in StrategyState.__dataclass_fields__:
        setattr(state, name, getattr(projected, name))
    return {
        "ok": True,
        "recovered": len(candidates) + recovered_terminal,
        "recovered_signal_keys": [str(row.get("signal_key", "")) for row in candidates],
    }


class LiveExecutionEngine:
    """Order idempotency and exchange-status reconciliation boundary."""

    def __init__(self, adapter: ExecutionAdapter, ledger: LiveExecutionLedger):
        self.adapter = adapter
        self.ledger = ledger

    def execute(
        self,
        decision: StrategyDecision,
        state: StrategyState,
        *,
        strategy_equity: float,
        mark_price: float,
        symbol_rules: dict[str, Any],
        exchange_available_balance: Optional[float] = None,
    ) -> dict[str, Any]:
        if not decision.action:
            return {"ok": True, "submitted": False, "reason": "NO_ACTION"}
        previous = self.ledger.latest_by_signal_key(decision.signal_key)
        retry_requested_qty: Optional[float] = None
        if previous and previous.get("status") != UNKNOWN_STATUS:
            return {
                "ok": True,
                "submitted": False,
                "duplicate_blocked": True,
                "status": previous.get("status"),
            }
        if previous and previous.get("status") == UNKNOWN_STATUS:
            recovered = self.adapter.query_order(
                client_order_id=decision.client_order_id,
                exchange_order_id=str(previous.get("exchange_order_id", "")),
            )
            if recovered is not None:
                return self._record_exchange_status(
                    decision, state, recovered,
                    requested_qty=float(previous.get("requested_qty", 0.0) or 0.0),
                    strategy_equity_before=strategy_equity,
                )
            # A retry is allowed only after the exchange explicitly reports the
            # client order id absent.  The same id is reused.
            retry_requested_qty = float(previous.get("requested_qty", 0.0) or 0.0)

        try:
            invariants = self._runtime_order_invariants(
                decision.action,
                state,
                strategy_equity=strategy_equity,
            )
        except Exception:
            if decision.action in RISK_INCREASE_ACTIONS:
                self._expire_unsubmitted_risk_increase(
                    decision,
                    state,
                    strategy_equity=strategy_equity,
                    reason="RUNTIME_INVARIANT_CHECK_ERROR",
                )
                return {
                    "ok": False,
                    "submitted": False,
                    "reason": "RUNTIME_INVARIANT_BLOCKED",
                    "invariants": {"ok": False, "reason": "INVARIANT_CHECK_ERROR"},
                }
            raise
        if invariants.get("ok") is not True:
            if decision.action in RISK_INCREASE_ACTIONS:
                self._expire_unsubmitted_risk_increase(
                    decision,
                    state,
                    strategy_equity=strategy_equity,
                    reason="RUNTIME_INVARIANT_BLOCKED",
                    details=invariants,
                )
            return {
                "ok": False,
                "submitted": False,
                "reason": "RUNTIME_INVARIANT_BLOCKED",
                "invariants": invariants,
            }

        requested_qty = retry_requested_qty or self._requested_qty(
            decision.action,
            state,
            strategy_equity=strategy_equity,
            exchange_available_balance=exchange_available_balance,
            mark_price=mark_price,
            symbol_rules=symbol_rules,
            leverage=int(invariants.get("selected_leverage", 0) or 0),
        )
        if requested_qty <= 0:
            if decision.action in RISK_INCREASE_ACTIONS:
                self._expire_unsubmitted_risk_increase(
                    decision,
                    state,
                    strategy_equity=strategy_equity,
                    reason="INVALID_OR_ZERO_QUANTITY",
                )
            return {"ok": False, "submitted": False, "reason": "INVALID_OR_ZERO_QUANTITY"}

        base = self._base_record(
            decision,
            requested_qty=requested_qty,
            strategy_equity_before=strategy_equity,
        )
        self.ledger.append({**base, "status": "SIGNAL_CONFIRMED"})
        self.ledger.append({**base, "status": "SUBMITTING"})
        side = "BUY" if decision.action in RISK_INCREASE_ACTIONS else "SELL"
        reduce_only = decision.action in RISK_REDUCTION_ACTIONS
        try:
            response = self.adapter.submit_market_order(
                side=side,
                quantity=requested_qty,
                client_order_id=decision.client_order_id,
                reduce_only=reduce_only,
                position_side=str(invariants.get("position_side", "BOTH")),
            )
        except (TimeoutError, ConnectionError, OSError):
            recovered = self.adapter.query_order(client_order_id=decision.client_order_id)
            if recovered is None:
                self.ledger.append({**base, "status": UNKNOWN_STATUS})
                return {"ok": False, "submitted": True, "status": UNKNOWN_STATUS}
            response = recovered
        return self._record_exchange_status(
            decision,
            state,
            response,
            requested_qty=requested_qty,
            strategy_equity_before=strategy_equity,
        )

    def reconcile_order(
        self,
        decision: StrategyDecision,
        state: StrategyState,
        *,
        strategy_equity: float,
    ) -> dict[str, Any]:
        previous = self.ledger.latest_by_signal_key(decision.signal_key)
        if previous is None:
            return {"ok": False, "reason": "LOCAL_ORDER_NOT_FOUND"}
        response = self.adapter.query_order(
            client_order_id=decision.client_order_id,
            exchange_order_id=str(previous.get("exchange_order_id", "")),
        )
        if response is None:
            unknown = dict(previous)
            unknown["status"] = UNKNOWN_STATUS
            unknown["recorded_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            self.ledger.append(unknown)
            return {"ok": False, "status": UNKNOWN_STATUS}
        return self._record_exchange_status(
            decision,
            state,
            response,
            requested_qty=float(previous.get("requested_qty", 0.0) or 0.0),
            strategy_equity_before=strategy_equity,
        )

    def sync_funding_income(self) -> dict[str, Any]:
        """Append each exchange funding income event exactly once."""
        existing = {
            str(row.get("signal_key", ""))
            for row in self.ledger.read()
            if row.get("status") == "ACCOUNT_INCOME"
        }
        appended = 0
        for row in self.adapter.get_income(income_type="FUNDING_FEE"):
            event_id = str(row.get("tranId", "") or f"{row.get('time','')}:{row.get('income','')}")
            signal_key = f"{STRATEGY_ID}:{SYMBOL}:FUNDING:{event_id}"
            if signal_key in existing:
                continue
            epoch_ms = int(float(row.get("time", 0) or 0))
            recorded_at = (
                datetime.fromtimestamp(epoch_ms / 1000.0, timezone.utc).isoformat(timespec="milliseconds")
                if epoch_ms > 0 else datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            )
            self.ledger.append({
                "strategy_id": STRATEGY_ID,
                "signal_key": signal_key,
                "symbol": SYMBOL,
                "timeframe": TIMEFRAME,
                "bar_close_time": recorded_at,
                "action": "FUNDING_PAYMENT",
                "status": "ACCOUNT_INCOME",
                "requested_qty": 0.0,
                "filled_qty": 0.0,
                "average_fill_price": 0.0,
                "client_order_id": "",
                "exchange_order_id": "",
                "fee": 0.0,
                "fee_asset": str(row.get("asset", "USDT")),
                "funding": float(row.get("income", 0.0) or 0.0),
                "realized_pnl": 0.0,
                "net_realized_pnl": float(row.get("income", 0.0) or 0.0),
                "realized_slippage": 0.0,
                "strategy_equity_before": 0.0,
                "strategy_equity_after": 0.0,
                "exchange_snapshot": _sanitize_exchange_snapshot(row),
                "recorded_at": recorded_at,
            })
            existing.add(signal_key)
            appended += 1
        return {"ok": True, "appended": appended}

    @staticmethod
    def _requested_qty(
        action: str,
        state: StrategyState,
        *,
        strategy_equity: float,
        exchange_available_balance: Optional[float],
        mark_price: float,
        symbol_rules: dict[str, Any],
        leverage: int = 1,
    ) -> float:
        if mark_price <= 0:
            return 0.0
        if action == LiveAction.OPEN.value:
            if exchange_available_balance is not None and float(exchange_available_balance) < SIZING_BASE_USDT:
                return 0.0
            raw_qty = safe_initial_notional(strategy_equity, leverage) / mark_price
        elif action == LiveAction.REDUCE_50.value:
            raw_qty = max(
                0.0,
                state.actual_position_qty - state.full_position_qty * 0.5,
            )
        elif action == LiveAction.ADD_50.value:
            raw_qty = min(
                max(state.reduced_qty, 0.0),
                max(state.full_position_qty - state.actual_position_qty, 0.0),
            )
        elif action in {
            LiveAction.STOP_CLOSE.value,
            LiveAction.TAKE_PROFIT_CLOSE.value,
            LiveAction.HARD_STOP_CLOSE.value,
        }:
            raw_qty = state.actual_position_qty
        else:
            return 0.0
        resolved_rules = dict(symbol_rules)
        if action in RISK_REDUCTION_ACTIONS:
            # Closing/reducing an existing position must not be blocked by the
            # entry notional gate. Quantity precision and minQty still apply.
            resolved_rules["min_notional"] = 0.0
        normalized = normalize_order_params(price=mark_price, qty=raw_qty, rules=resolved_rules)
        normalized_qty = float(normalized["normalized_qty"]) if normalized["is_valid"] else 0.0
        if action == LiveAction.REDUCE_50.value and normalized_qty > 0:
            half_target = state.full_position_qty * 0.5
            expected_remaining = state.actual_position_qty - normalized_qty
            step_size = float(resolved_rules.get("step_size", 0.0) or 0.0)
            tolerance = max(1e-12, step_size * 1e-9)
            if expected_remaining < half_target - tolerance:
                return 0.0
        return normalized_qty

    def _runtime_order_invariants(
        self,
        action: str,
        state: StrategyState,
        *,
        strategy_equity: float,
    ) -> dict[str, Any]:
        if action in RISK_INCREASE_ACTIONS:
            reconciliation = reconcile_startup(state, self.ledger, self.adapter)
            if reconciliation.get("ok") is not True:
                return {"ok": False, "reason": reconciliation.get("reason", "RECONCILIATION_FAILED")}
            try:
                fixed_allowed = fixed_leverage_allowed(self.adapter.get_leverage_brackets())
            except Exception:
                return {"ok": False, "reason": "FIXED_50X_PERMISSION_UNAVAILABLE"}
            symbol_config = self.adapter.get_symbol_config()
            leverage_fixed_50x = int(float(symbol_config.get("leverage", 0) or 0)) == FIXED_LEVERAGE
            dual_side = _dual_side_mode(self.adapter.get_position_mode())
            position_side = "LONG" if dual_side else "BOTH"
            self.adapter.get_account()  # authenticated PAPI access must remain healthy
            available_balance = usdt_available_balance(self.adapter.get_balance())
            restrictions = self.adapter.get_api_restrictions()
            managed_capital = min(max(float(strategy_equity), 0.0), LIVE_CAPITAL_CAP_USDT)
            checks = {
                "reconciliation": True,
                "position_mode_supported": True,
                "long_only_position_side": position_side in {"BOTH", "LONG"},
                "portfolio_margin_account": True,
                "fixed_50x_allowed": fixed_allowed,
                "leverage_fixed_50x": leverage_fixed_50x,
                "capital_cap": managed_capital <= LIVE_CAPITAL_CAP_USDT,
                "sizing_base_available": available_balance >= SIZING_BASE_USDT,
                "api_trade": _to_bool(restrictions.get("enablePortfolioMarginTrading")),
                "withdrawal_disabled": not _to_bool(restrictions.get("enableWithdrawals")),
                "no_unrecognized_open_orders": True,
            }
            return {
                "ok": all(checks.values()),
                "checks": checks,
                "gate": "RISK_INCREASE_FULL",
                "selected_leverage": FIXED_LEVERAGE,
                "account_mode": ACCOUNT_MODE,
                "api_mode": API_MODE,
                "position_mode": "HEDGE" if dual_side else "ONE_WAY",
                "position_side": position_side,
                "capital_cap_usdt": LIVE_CAPITAL_CAP_USDT,
                "sizing_base_usdt": SIZING_BASE_USDT,
            }

        if action not in RISK_REDUCTION_ACTIONS:
            return {"ok": False, "reason": "UNKNOWN_ACTION_GATE"}

        # Risk-reducing orders must remain available when leverage or account
        # equity has drifted. They still require a
        # clearly identified one-way LONG and no conflicting exchange order.
        position = self.adapter.get_position()
        exchange_qty = position_quantity(position)
        if exchange_qty <= 1e-12:
            return {
                "ok": False,
                "reason": "NO_CONFIRMED_LONG_POSITION_TO_REDUCE",
                "exchange_qty": exchange_qty,
                "gate": "RISK_REDUCTION_SAFE",
            }
        dual_side = _dual_side_mode(self.adapter.get_position_mode())
        position_side = "LONG" if dual_side else "BOTH"

        open_orders = self.adapter.get_open_orders()
        latest: dict[str, dict[str, Any]] = {}
        for row in self.ledger.read():
            signal_key = str(row.get("signal_key", ""))
            if signal_key:
                latest[signal_key] = row
        pending = [
            row for row in latest.values()
            if row.get("status") in {"SIGNAL_CONFIRMED", "SUBMITTING", "NEW", "PARTIALLY_FILLED", UNKNOWN_STATUS}
        ]
        known_clients = {str(row.get("client_order_id", "")) for row in pending if row.get("client_order_id")}
        unknown_exchange_orders = [
            item for item in open_orders
            if str(item.get("clientOrderId", item.get("client_order_id", ""))) not in known_clients
        ]
        if unknown_exchange_orders:
            return {
                "ok": False,
                "reason": "UNRECOGNIZED_EXCHANGE_OPEN_ORDER",
                "gate": "RISK_REDUCTION_SAFE",
            }

        # Exchange quantity is authoritative for a reduce-only exit.  Sync it
        # before sizing so a stale local quantity cannot accidentally leave a
        # larger live exposure behind or request an unsafe amount.
        state.actual_position_qty = exchange_qty
        if action == LiveAction.REDUCE_50.value and state.full_position_qty <= 1e-12:
            return {
                "ok": False,
                "reason": "FULL_POSITION_TARGET_UNKNOWN",
                "gate": "RISK_REDUCTION_SAFE",
            }
        advisory = {"account_mode": ACCOUNT_MODE, "leverage_fixed_50x": None}
        return {
            "ok": True,
            "gate": "RISK_REDUCTION_SAFE",
            "position_mode": "HEDGE" if dual_side else "ONE_WAY",
            "position_side": position_side,
            "exchange_qty": exchange_qty,
            "checks": {
                "confirmed_long": True,
                "long_only_position_side": True,
                "no_unrecognized_open_orders": True,
            },
            "advisory_drift": advisory,
        }

    def _expire_unsubmitted_risk_increase(
        self,
        decision: StrategyDecision,
        state: StrategyState,
        *,
        strategy_equity: float,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        if decision.action not in RISK_INCREASE_ACTIONS:
            return
        existing = self.ledger.latest_by_signal_key(decision.signal_key)
        if existing is None or existing.get("status") != STALE_RISK_INCREASE_STATUS:
            record = self._base_record(
                decision,
                requested_qty=0.0,
                strategy_equity_before=strategy_equity,
            )
            record.update({
                "status": STALE_RISK_INCREASE_STATUS,
                "reason": reason,
                "exchange_snapshot": {"pre_submit_block": dict(details or {})},
                "recorded_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            })
            self.ledger.append(record)
        state.pending_action = ""
        state.pending_decision = {}
        state.recovery_status = STALE_RISK_INCREASE_STATUS
        state.recovery_decision = {}

    @staticmethod
    def _base_record(
        decision: StrategyDecision,
        *,
        requested_qty: float,
        strategy_equity_before: float,
    ) -> dict[str, Any]:
        return {
            "strategy_id": STRATEGY_ID,
            "signal_key": decision.signal_key,
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "bar_close_time": decision.bar_close_time,
            "action": decision.action,
            "signal_price": decision.signal_price,
            "entry_low": decision.entry_low,
            "reason": decision.reason,
            "requested_qty": requested_qty,
            "filled_qty": 0.0,
            "average_fill_price": 0.0,
            "client_order_id": decision.client_order_id,
            "exchange_order_id": "",
            "fee": 0.0,
            "fee_asset": "",
            "funding": 0.0,
            "realized_pnl": 0.0,
            "net_realized_pnl": 0.0,
            "realized_slippage": 0.0,
            "strategy_equity_before": float(strategy_equity_before),
            "strategy_equity_after": float(strategy_equity_before),
            "live_capital_cap_usdt": LIVE_CAPITAL_CAP_USDT,
            "account_mode": ACCOUNT_MODE,
            "api_mode": API_MODE,
            "sizing_base_usdt": SIZING_BASE_USDT,
            "leverage_mode": "FIXED",
            "leverage": FIXED_LEVERAGE,
            "target_initial_notional_usdt": TARGET_INITIAL_NOTIONAL_USDT,
            "exchange_snapshot": {},
            "live_safety_deviations": list(APPROVED_LIVE_SAFETY_DEVIATIONS),
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }

    def _record_exchange_status(
        self,
        decision: StrategyDecision,
        state: StrategyState,
        response: dict[str, Any],
        *,
        requested_qty: float,
        strategy_equity_before: float,
    ) -> dict[str, Any]:
        status = str(response.get("status", "")).upper()
        if status not in ORDER_STATUSES:
            status = UNKNOWN_STATUS
        filled_qty = float(response.get("executedQty", response.get("filled_qty", 0.0)) or 0.0)
        average_price = float(response.get("avgPrice", response.get("average_fill_price", 0.0)) or 0.0)
        exchange_order_id = str(response.get("orderId", response.get("exchange_order_id", "")) or "")
        evidence = self._fill_evidence(exchange_order_id) if filled_qty > 0 else {}
        if average_price <= 0:
            average_price = float(evidence.get("average_fill_price", 0.0) or 0.0)
        fee = float(evidence.get("fee", 0.0))
        realized_pnl = float(evidence.get("realized_pnl", 0.0))
        # Portfolio Margin account equity may include unrelated collateral and
        # must never scale or overwrite this strategy's fixed 50 USDT ledger.
        equity_after = strategy_equity_before + realized_pnl - fee
        record = {
            **self._base_record(
                decision,
                requested_qty=requested_qty,
                strategy_equity_before=strategy_equity_before,
            ),
            "status": status,
            "filled_qty": filled_qty,
            "average_fill_price": average_price,
            "exchange_order_id": exchange_order_id,
            "fee": fee,
            "fee_asset": evidence.get("fee_asset", ""),
            "realized_pnl": realized_pnl,
            "net_realized_pnl": realized_pnl - fee,
            "realized_slippage": _realized_slippage(
                action=str(decision.action),
                signal_price=float(decision.signal_price),
                average_fill_price=average_price,
                filled_qty=filled_qty,
            ),
            "strategy_equity_after": equity_after,
            "exchange_snapshot": _sanitize_exchange_snapshot(response),
        }
        previous = self.ledger.latest_by_signal_key(decision.signal_key)
        if (
            previous
            and previous.get("status") == status
            and float(previous.get("filled_qty", 0.0) or 0.0) == filled_qty
            and str(previous.get("exchange_order_id", "")) == exchange_order_id
        ):
            return {
                "ok": status in {"NEW", "PARTIALLY_FILLED", "FILLED"},
                "submitted": False,
                "status": status,
                "filled_qty": filled_qty,
                "exchange_order_id": exchange_order_id,
                "unchanged": True,
            }
        self.ledger.append(record)
        if status == "FILLED":
            Zec4hStrategy.apply_filled_action(
                state,
                decision,
                filled_qty=filled_qty,
                average_fill_price=average_price,
            )
            if decision.action in RISK_INCREASE_ACTIONS and state.actual_position_qty > 1e-12:
                if (
                    not state.stop_guard_active
                    or state.stop_guard_price is None
                    or not state.take_profit_active
                    or state.take_profit_price is None
                ):
                    _arm_terminal_safety_exit(
                        state,
                        decision,
                        status="EXIT_GUARD_CREATION_FAILED",
                        exchange_qty=state.actual_position_qty,
                        partial_fill=False,
                    )
        elif status in TERMINAL_FAILURE_STATUSES:
            state.pending_action = ""
            state.pending_decision = {}
            state.recovery_status = ""
            state.recovery_decision = {}
            if filled_qty > 0:
                _apply_partial_terminal_transition(
                    state,
                    decision,
                    status=status,
                    filled_qty=filled_qty,
                )
            else:
                state.phase = StrategyPhase.HARD_STOP.value
                state.hard_stop_reason = f"ORDER_{status}"
            try:
                exchange_qty = position_quantity(self.adapter.get_position())
            except Exception:
                state.phase = StrategyPhase.HARD_STOP.value
                state.recovery_status = "TERMINAL_POSITION_UNVERIFIED"
                state.recovery_decision = {}
            else:
                _arm_terminal_safety_exit(
                    state,
                    decision,
                    status=status,
                    exchange_qty=exchange_qty,
                    partial_fill=filled_qty > 0,
                )
        return {
            "ok": status in {"NEW", "PARTIALLY_FILLED", "FILLED"},
            "submitted": True,
            "status": status,
            "filled_qty": filled_qty,
            "exchange_order_id": exchange_order_id,
            "safety_exit_required": state.recovery_status in {
                "PARTIAL_TERMINAL_SAFETY_EXIT_REQUIRED",
                "TERMINAL_SAFETY_EXIT_REQUIRED",
            },
        }

    def _fill_evidence(self, exchange_order_id: str) -> dict[str, Any]:
        if not exchange_order_id:
            return {}
        try:
            fills = self.adapter.get_fills(order_id=exchange_order_id)
        except Exception:
            return {}
        matching = [row for row in fills if str(row.get("orderId", "")) == exchange_order_id]
        fee = sum(float(row.get("commission", 0.0) or 0.0) for row in matching)
        realized = sum(float(row.get("realizedPnl", 0.0) or 0.0) for row in matching)
        quantities = [float(row.get("qty", row.get("quantity", 0.0)) or 0.0) for row in matching]
        total_qty = sum(quantities)
        total_quote = sum(
            float(row.get("price", 0.0) or 0.0) * qty
            for row, qty in zip(matching, quantities)
        )
        assets = {str(row.get("commissionAsset", "")) for row in matching if row.get("commissionAsset")}
        return {
            "fee": fee,
            "fee_asset": next(iter(assets)) if len(assets) == 1 else ("MULTIPLE" if assets else ""),
            "realized_pnl": realized,
            "average_fill_price": total_quote / total_qty if total_qty > 0 else 0.0,
        }


def _sanitize_exchange_snapshot(response: dict[str, Any]) -> dict[str, Any]:
    blocked = {"signature", "apikey", "api_key", "api_secret", "secret"}
    return {key: value for key, value in response.items() if str(key).lower() not in blocked}


def _realized_slippage(*, action: str, signal_price: float, average_fill_price: float, filled_qty: float) -> float:
    if min(signal_price, average_fill_price, filled_qty) <= 0:
        return 0.0
    if action in {LiveAction.OPEN.value, LiveAction.ADD_50.value}:
        return (average_fill_price - signal_price) * filled_qty
    return (signal_price - average_fill_price) * filled_qty


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _dual_side_mode(payload: dict[str, Any]) -> bool:
    if "dualSidePosition" not in payload:
        raise ValueError("POSITION_MODE_UNAVAILABLE")
    value = payload.get("dualSidePosition")
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError("POSITION_MODE_UNAVAILABLE")
    return normalized == "true"
