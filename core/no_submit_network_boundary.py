from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitNetworkBoundary:
    pattern: str
    blocked: bool
    description: str


NETWORK_PATTERNS: tuple[NoSubmitNetworkBoundary, ...] = (
    NoSubmitNetworkBoundary(
        pattern="outbound_http_exchange",
        blocked=True,
        description="HTTP requests to any exchange API host",
    ),
    NoSubmitNetworkBoundary(
        pattern="websocket_exchange",
        blocked=True,
        description="WebSocket connections to exchange streaming endpoints",
    ),
    NoSubmitNetworkBoundary(
        pattern="rest_trading_platform",
        blocked=True,
        description="REST calls to Binance or any trading platform API",
    ),
)
