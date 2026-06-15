"""MACD Rebound Signal Plugin — StrategyPlugin adapter for MACD rebound detection.

Wraps the existing SignalEngine to produce SignalEnvelopes from fixture candle data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.signal_envelope import ALLOWED_MODES, SignalEnvelope
from core.market_data_contract import Candle
from utils.indicators import macd


@dataclass
class StrategyResult:
    """Result from a strategy plugin run."""
    signals: list[SignalEnvelope] = field(default_factory=list)
    candles_processed: int = 0
    strategy_id: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": [s.to_dict() for s in self.signals],
            "candles_processed": self.candles_processed,
            "strategy_id": self.strategy_id,
            "errors": self.errors,
            "signal_count": len(self.signals),
        }


@dataclass
class StrategyPlugin:
    """Base class for strategy plugins."""
    strategy_id: str = ""
    mode: str = "paper"
    dry_run: bool = True

    def run(self, candles: list[Candle]) -> StrategyResult:
        raise NotImplementedError


class MACDReboundSignalPlugin(StrategyPlugin):
    """MACD Rebound strategy plugin.

    Processes fixture candles through the existing SignalEngine and wraps
    raw signals into SignalEnvelopes.
    """
    strategy_id: str = "macd_rebound_v1"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        mode: str = "paper",
        dry_run: bool = True,
    ) -> None:
        if not dry_run:
            raise ValueError("MACDReboundSignalPlugin requires dry_run=True")
        if mode not in ALLOWED_MODES:
            raise ValueError(f"mode must be one of {sorted(ALLOWED_MODES)}")
        super().__init__(strategy_id="macd_rebound_v1", mode=mode, dry_run=dry_run)
        self._config = config or {}
        plugin_cfg = self._config.get("macd_rebound", {})
        self._macd_fast = int(plugin_cfg.get("fast", 12))
        self._macd_slow = int(plugin_cfg.get("slow", 26))
        self._macd_signal = int(plugin_cfg.get("signal", 9))
        self._engine: Any = None

    def _get_engine(self) -> Any:
        if self._engine is None:
            from core.signal_engine import SignalEngine
            import logging
            logger = logging.getLogger("macd_rebound_plugin")
            self._engine = SignalEngine(self._config, logger)
        return self._engine

    def run(self, candles: list[Candle]) -> StrategyResult:
        engine = self._get_engine()
        result = StrategyResult(strategy_id=self.strategy_id)
        has_position = False
        hold_counter = 0

        for index, candle in enumerate(candles):
            candle_dict = candle.to_dict()
            raw = engine.on_candle(candle_dict, has_position)
            result.candles_processed += 1

            if raw.get("action") == "SHORT":
                macd_context = self._macd_context(candles[: index + 1])
                if not macd_context["bearish"]:
                    continue
                try:
                    envelope = SignalEnvelope(
                        strategy_id=self.strategy_id,
                        symbol=raw["symbol"],
                        timeframe=candle.timeframe,
                        side="short",
                        signal_type="entry",
                        entry=raw["entry"],
                        stop_loss=raw["stop"],
                        take_profit=raw["tp"],
                        confidence=min(raw.get("score", 0) / 10.0, 1.0),
                        risk_score=0.5,
                        metadata={**raw.get("meta", {}), **macd_context},
                        dry_run=self.dry_run,
                        mode=self.mode,
                    )
                    result.signals.append(envelope)
                    has_position = True
                    hold_counter = 0
                    engine.on_position_opened()
                except Exception as e:
                    result.errors.append(f"signal_envelope_error: {e}")

            if has_position and raw.get("action") == "NONE":
                hold_counter += 1
                if hold_counter >= 3:
                    has_position = False
                    hold_counter = 0
                    engine.on_trade_closed({})

        return result

    def _macd_context(self, candles: list[Candle]) -> dict[str, Any]:
        closes = [c.close for c in candles]
        dif, dea, hist = macd(closes, self._macd_fast, self._macd_slow, self._macd_signal)
        bearish = bool(hist < 0)
        return {
            "macd_dif": dif,
            "macd_dea": dea,
            "macd_hist": hist,
            "macd_bearish": bearish,
            "bearish": bearish,
        }

    def reset(self) -> None:
        self._engine = None
        if hasattr(self, "_hold_counter"):
            del self._hold_counter
