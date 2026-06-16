"""Tests for strategy registry."""
from __future__ import annotations

import pytest

from core.paper_trading.strategy_registry import (
    StrategyMeta, StrategyRegistry, create_default_registry,
    MACD_REBOUND_META,
)


class TestStrategyRegistry:
    def test_default_registry_has_macd(self):
        reg = create_default_registry()
        assert reg.has("macd_rebound")

    def test_get_signal_fn(self):
        reg = create_default_registry()
        fn = reg.get_signal_fn("macd_rebound")
        assert callable(fn)

    def test_get_meta(self):
        reg = create_default_registry()
        meta = reg.get_meta("macd_rebound")
        assert meta.name == "macd_rebound"
        assert meta.paper_only is True

    def test_unknown_strategy_raises(self):
        reg = create_default_registry()
        with pytest.raises(KeyError, match="Unknown strategy"):
            reg.get_signal_fn("nonexistent")

    def test_duplicate_register_raises(self):
        reg = create_default_registry()
        with pytest.raises(ValueError, match="already registered"):
            reg.register("macd_rebound", lambda: None, MACD_REBOUND_META)

    def test_non_paper_only_rejected(self):
        reg = StrategyRegistry()
        meta = StrategyMeta(
            name="bad", version="1.0", description="",
            required_fields=[], default_params={},
            paper_only=False,
        )
        with pytest.raises(ValueError, match="paper_only"):
            reg.register("bad", lambda: None, meta)

    def test_meta_complete(self):
        meta = MACD_REBOUND_META
        assert len(meta.required_fields) > 0
        assert "entry_price" in meta.required_fields
        assert "stop_loss" in meta.required_fields
        assert meta.paper_only is True

    def test_list_strategies(self):
        reg = create_default_registry()
        strategies = reg.list_strategies()
        assert "macd_rebound" in strategies

    def test_register_custom(self):
        reg = StrategyRegistry()
        meta = StrategyMeta(
            name="custom", version="0.1", description="test",
            required_fields=["symbol"], default_params={},
            paper_only=True,
        )
        reg.register("custom", lambda bars, i: None, meta)
        assert reg.has("custom")
        assert "custom" in reg.list_strategies()

    def test_no_network(self):
        import core.paper_trading.strategy_registry as mod
        source = open(mod.__file__).read()
        assert "requests" not in source
        assert "httpx" not in source
        assert "importlib" not in source
