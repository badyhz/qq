from dataclasses import dataclass


@dataclass(frozen=True)
class OfflineShadowSymbol:
    symbol: str
    base_asset: str
    quote_asset: str
    exchange: str
