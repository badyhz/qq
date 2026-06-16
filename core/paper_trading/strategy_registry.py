"""Strategy registry — local strategy lookup, no network, no dynamic imports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, List


@dataclass(frozen=True)
class StrategyMeta:
    name: str
    version: str
    description: str
    required_fields: List[str]
    default_params: Dict[str, Any]
    paper_only: bool = True


class StrategyRegistry:
    """Local strategy registry. No network, no dynamic imports."""

    def __init__(self) -> None:
        self._strategies: Dict[str, tuple[Callable, StrategyMeta]] = {}

    def register(self, name: str, signal_fn: Callable, meta: StrategyMeta) -> None:
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' already registered")
        if not meta.paper_only:
            raise ValueError(f"Strategy '{name}' must be paper_only=True")
        self._strategies[name] = (signal_fn, meta)

    def get_signal_fn(self, name: str) -> Callable:
        if name not in self._strategies:
            raise KeyError(f"Unknown strategy: {name}")
        return self._strategies[name][0]

    def get_meta(self, name: str) -> StrategyMeta:
        if name not in self._strategies:
            raise KeyError(f"Unknown strategy: {name}")
        return self._strategies[name][1]

    def list_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    def has(self, name: str) -> bool:
        return name in self._strategies


def _macd_rebound_signal(bars, i):
    """MACD rebound signal for registry."""
    if i < 10:
        return None
    recent_high = max(b.high for b in bars[max(0, i - 10):i])
    current = bars[i].close
    drop_pct = (recent_high - current) / recent_high * 100
    if drop_pct >= 3.0 and bars[i].close > bars[i].open:
        return {
            "symbol": "BTCUSDT", "side": "BUY",
            "entry_price": current,
            "stop_loss": current * 0.98,
            "take_profit": current * 1.06,
            "invalidation_price": current * 0.97,
            "signal_source": "macd_rebound",
        }
    return None


MACD_REBOUND_META = StrategyMeta(
    name="macd_rebound",
    version="1.0.0",
    description="Buy on 3%+ drop from recent high, confirmed by bullish candle",
    required_fields=["symbol", "side", "entry_price", "stop_loss", "take_profit", "invalidation_price"],
    default_params={"drop_pct_threshold": 3.0, "lookback": 10},
    paper_only=True,
)


def create_default_registry() -> StrategyRegistry:
    """Create registry with built-in strategies."""
    registry = StrategyRegistry()
    registry.register("macd_rebound", _macd_rebound_signal, MACD_REBOUND_META)
    return registry
