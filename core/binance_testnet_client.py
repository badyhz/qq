from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.error import HTTPError
from typing import Any, Mapping, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def make_client_order_id(prefix: str, symbol: str, timestamp: Any) -> str:
    max_len = 35
    clean_prefix = "".join(ch for ch in str(prefix or "dr").lower() if ch.isalnum()) or "dr"
    clean_symbol = "".join(ch for ch in str(symbol or "").upper() if ch.isalnum()) or "SYM"
    # Keep symbol compact to guarantee Binance futures < 36 chars constraint.
    clean_symbol = clean_symbol[:19]
    ts_text = str(timestamp if timestamp is not None else "").strip()
    ts_digits = "".join(ch for ch in ts_text if ch.isdigit())
    if not ts_digits:
        ts_digits = str(int(time.time() * 1000))
    ts_tail = ts_digits[-12:]
    candidate = f"{clean_prefix}_{clean_symbol}_{ts_tail}"
    if len(candidate) <= max_len:
        return candidate
    # Enforce hard upper bound by trimming symbol first, then tail if still needed.
    overflow = len(candidate) - max_len
    if overflow > 0:
        clean_symbol = clean_symbol[: max(1, len(clean_symbol) - overflow)]
        candidate = f"{clean_prefix}_{clean_symbol}_{ts_tail}"
    if len(candidate) > max_len:
        candidate = candidate[:max_len]
    return candidate


class BinanceFuturesTestnetClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        base_url: str = "https://demo-fapi.binance.com",
        timeout_sec: float = 10.0,
    ):
        self.api_key = str(api_key or "").strip()
        self.api_secret = str(api_secret or "").strip()
        self.base_url = str(base_url or "https://demo-fapi.binance.com").rstrip("/")
        self.timeout_sec = float(timeout_sec)

    def _signed_request(
        self,
        *,
        path: str,
        method: str,
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        query = {str(k): str(v) for k, v in dict(params or {}).items() if v is not None and str(v) != ""}
        if "timestamp" not in query:
            query["timestamp"] = str(int(time.time() * 1000))
        if "recvWindow" not in query:
            query["recvWindow"] = "5000"
        canonical = urlencode(query)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed_query = f"{canonical}&signature={signature}"
        request_url = f"{self.base_url}{path}"
        body: Optional[bytes] = None
        request_method = str(method or "GET").strip().upper()
        if request_method == "GET":
            request_url = f"{request_url}?{signed_query}"
        else:
            body = signed_query.encode("utf-8")
        request = Request(
            request_url,
            data=body,
            method=request_method,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-MBX-APIKEY": self.api_key,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return {
                    "ok": True,
                    "status_code": int(getattr(resp, "status", 200) or 200),
                    "response": payload,
                    "error_code": "",
                    "error_message": "",
                }
        except HTTPError as exc:
            response_text = ""
            response_json: dict[str, Any] = {}
            try:
                response_text = exc.read().decode("utf-8")
                if response_text:
                    parsed = json.loads(response_text)
                    if isinstance(parsed, dict):
                        response_json = parsed
            except Exception:
                response_text = response_text or ""
            error_code = ""
            if isinstance(response_json.get("code"), (int, float, str)):
                error_code = str(response_json.get("code"))
            if not error_code:
                error_code = str(exc.code or "HTTPError")
            error_message = str(response_json.get("msg", "")).strip() or str(exc.reason or exc)
            return {
                "ok": False,
                "status_code": int(getattr(exc, "code", 0) or 0),
                "response": response_json if response_json else {"response_text": response_text},
                "error_code": error_code,
                "error_message": error_message,
            }
        except Exception as exc:
            return {
                "ok": False,
                "status_code": 0,
                "response": {},
                "error_code": exc.__class__.__name__,
                "error_message": str(exc),
            }

    def _public_request(
        self,
        *,
        path: str,
        method: str = "GET",
        params: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        query = {str(k): str(v) for k, v in dict(params or {}).items() if v is not None and str(v) != ""}
        request_url = f"{self.base_url}{path}"
        request_method = str(method or "GET").strip().upper()
        if request_method == "GET" and query:
            request_url = f"{request_url}?{urlencode(query)}"
        request = Request(request_url, method=request_method)
        try:
            with urlopen(request, timeout=self.timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return {
                    "ok": True,
                    "status_code": int(getattr(resp, "status", 200) or 200),
                    "response": payload,
                    "error_code": "",
                    "error_message": "",
                }
        except HTTPError as exc:
            response_text = ""
            response_json: dict[str, Any] = {}
            try:
                response_text = exc.read().decode("utf-8")
                if response_text:
                    parsed = json.loads(response_text)
                    if isinstance(parsed, dict):
                        response_json = parsed
            except Exception:
                response_text = response_text or ""
            error_code = ""
            if isinstance(response_json.get("code"), (int, float, str)):
                error_code = str(response_json.get("code"))
            if not error_code:
                error_code = str(exc.code or "HTTPError")
            error_message = str(response_json.get("msg", "")).strip() or str(exc.reason or exc)
            return {
                "ok": False,
                "status_code": int(getattr(exc, "code", 0) or 0),
                "response": response_json if response_json else {"response_text": response_text},
                "error_code": error_code,
                "error_message": error_message,
            }
        except Exception as exc:
            return {
                "ok": False,
                "status_code": 0,
                "response": {},
                "error_code": exc.__class__.__name__,
                "error_message": str(exc),
            }

    def create_order(self, params: Mapping[str, Any]) -> dict[str, Any]:
        return self._signed_request(path="/fapi/v1/order", method="POST", params=params)

    def create_algo_order(self, params: Mapping[str, Any]) -> dict[str, Any]:
        # Binance futures demo/testnet conditional orders must use Algo Order API.
        return self._signed_request(path="/fapi/v1/algoOrder", method="POST", params=params)

    def get_open_algo_orders(self, *, symbol: str, algo_type: str = "CONDITIONAL") -> dict[str, Any]:
        return self._signed_request(
            path="/fapi/v1/openAlgoOrders",
            method="GET",
            params={
                "symbol": str(symbol or "").strip().upper(),
                "algoType": str(algo_type or "CONDITIONAL").strip().upper(),
            },
        )

    def cancel_open_algo_orders(self, *, symbol: str, algo_type: str = "CONDITIONAL") -> dict[str, Any]:
        return self._signed_request(
            path="/fapi/v1/algoOpenOrders",
            method="DELETE",
            params={
                "symbol": str(symbol or "").strip().upper(),
                "algoType": str(algo_type or "CONDITIONAL").strip().upper(),
            },
        )

    def get_position_risk(self, *, symbol: str) -> dict[str, Any]:
        return self._signed_request(
            path="/fapi/v2/positionRisk",
            method="GET",
            params={"symbol": str(symbol or "").strip().upper()},
        )

    def get_exchange_info(self) -> dict[str, Any]:
        return self._public_request(path="/fapi/v1/exchangeInfo", method="GET")

    def get_order(
        self,
        *,
        symbol: str,
        order_id: Any = "",
        orig_client_order_id: str = "",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"symbol": str(symbol or "").strip().upper()}
        if str(order_id or "").strip():
            params["orderId"] = str(order_id).strip()
        if str(orig_client_order_id or "").strip():
            params["origClientOrderId"] = str(orig_client_order_id).strip()
        return self._signed_request(path="/fapi/v1/order", method="GET", params=params)

    def get_all_orders(
        self,
        *,
        symbol: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        params = {
            "symbol": str(symbol or "").strip().upper(),
            "limit": int(limit),
        }
        return self._signed_request(path="/fapi/v1/allOrders", method="GET", params=params)

    def get_algo_orders(
        self,
        *,
        symbol: str,
        algo_type: str = "CONDITIONAL",
    ) -> dict[str, Any]:
        params = {
            "symbol": str(symbol or "").strip().upper(),
            "algoType": str(algo_type or "CONDITIONAL").strip().upper(),
        }
        return self._signed_request(path="/fapi/v1/algoOrders", method="GET", params=params)

    def check_account_auth(self) -> dict[str, Any]:
        return self._signed_request(path="/fapi/v2/account", method="GET", params={})


def build_entry_market_order_params(
    *,
    symbol: str,
    side: str,
    quantity: Any,
    client_order_id: Optional[str] = None,
) -> dict[str, Any]:
    row = {
        "symbol": str(symbol or "").strip().upper(),
        "side": str(side or "").strip().upper(),
        "type": "MARKET",
        "quantity": quantity,
    }
    if client_order_id:
        client_id = str(client_order_id).strip()
        if len(client_id) > 35:
            client_id = make_client_order_id("dr", row["symbol"], client_id)
        row["newClientOrderId"] = client_id[:35]
    return row


def sanitize_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"raw_type": str(type(response).__name__)}
    blocked = {"api_key", "api_secret", "signature"}
    sanitized: dict[str, Any] = {}
    for key, value in response.items():
        if str(key).lower() in blocked:
            sanitized[key] = "***"
        else:
            sanitized[key] = value
    return sanitized
