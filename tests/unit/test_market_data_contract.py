"""Tests for core/market_data_contract.py — 10 scenarios."""
import pytest
from core.market_data_contract import (
    Candle,
    CandleSeries,
    MarketDataBatch,
    DataFeedMetadata,
)


class TestCandle:
    def test_candle_creation(self):
        c = Candle(symbol="BTCUSDT", timestamp="1000", open=100, high=110, low=90, close=105, volume=50)
        assert c.symbol == "BTCUSDT"
        assert c.close == 105
        assert c.is_fixture is True
        assert c.is_live is False

    def test_candle_to_dict_roundtrip(self):
        c = Candle(symbol="ETHUSDT", timestamp="2000", open=50, high=55, low=48, close=52, volume=30)
        d = c.to_dict()
        c2 = Candle.from_dict(d)
        assert c2.symbol == c.symbol
        assert c2.close == c.close
        assert c2.is_fixture is True

    def test_candle_validate_high_lt_low(self):
        c = Candle(symbol="X", timestamp="1", open=10, high=5, low=20, close=10, volume=1)
        errors = c.validate()
        assert any("high" in e and "low" in e for e in errors)

    def test_candle_validate_live_rejected(self):
        c = Candle(symbol="X", timestamp="1", open=10, high=10, low=10, close=10, volume=1, is_live=True)
        errors = c.validate()
        assert any("is_live" in e for e in errors)

    def test_candle_frozen(self):
        c = Candle(symbol="X", timestamp="1", open=10, high=10, low=10, close=10, volume=1)
        with pytest.raises(AttributeError):
            c.close = 20


class TestCandleSeries:
    def test_series_properties(self):
        candles = [
            Candle(symbol="BTC", timestamp=str(i), open=100, high=110, low=90, close=100 + i, volume=10 * i)
            for i in range(5)
        ]
        s = CandleSeries(symbol="BTC", candles=candles)
        assert s.count == 5
        assert s.is_empty is False
        assert s.closes == [100, 101, 102, 103, 104]
        assert len(s.highs) == 5

    def test_series_validate_live(self):
        s = CandleSeries(symbol="X", is_live=True)
        errors = s.validate()
        assert any("is_live" in e for e in errors)


class TestMarketDataBatch:
    def test_batch_symbols_and_total(self):
        s1 = CandleSeries(symbol="BTC", candles=[Candle(symbol="BTC", timestamp="1", open=1, high=1, low=1, close=1, volume=1)])
        s2 = CandleSeries(symbol="ETH", candles=[
            Candle(symbol="ETH", timestamp="1", open=1, high=1, low=1, close=1, volume=1),
            Candle(symbol="ETH", timestamp="2", open=1, high=1, low=1, close=1, volume=1),
        ])
        batch = MarketDataBatch(series={"BTC": s1, "ETH": s2})
        assert set(batch.symbols) == {"BTC", "ETH"}
        assert batch.total_candles == 3

    def test_batch_validate_empty(self):
        batch = MarketDataBatch(series={})
        errors = batch.validate()
        assert any("empty" in e for e in errors)


class TestDataFeedMetadata:
    def test_metadata_to_dict(self):
        m = DataFeedMetadata(feed_id="test.json", feed_type="fixture", symbols=["BTC"], candle_count=10)
        d = m.to_dict()
        assert d["feed_id"] == "test.json"
        assert d["is_fixture"] is True
        assert d["is_live"] is False
