from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitExchangeClientBoundary:
    client_class: str
    blocked: bool
    description: str


EXCHANGE_CLIENTS: tuple[NoSubmitExchangeClientBoundary, ...] = (
    NoSubmitExchangeClientBoundary(
        client_class="BinanceConnector",
        blocked=True,
        description="BinanceConnector must not be instantiated",
    ),
    NoSubmitExchangeClientBoundary(
        client_class="BinanceTestnetClient",
        blocked=True,
        description="BinanceTestnetClient must not be repurposed for live",
    ),
    NoSubmitExchangeClientBoundary(
        client_class="ExchangeFactory",
        blocked=True,
        description="No factory function may produce a live exchange client",
    ),
)
