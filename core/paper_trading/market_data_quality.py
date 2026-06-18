"""Market data quality validator — checks OHLCV bar integrity."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from core.paper_trading.data_source import MarketBar


@dataclass(frozen=True)
class QualityReport:
    symbol: str
    timeframe: str
    total_bars: int
    valid_bars: int
    invalid_bars: int
    issues: List[str]

    @property
    def ok(self) -> bool:
        return self.invalid_bars == 0 and not self.issues

    @property
    def valid_ratio(self) -> float:
        if self.total_bars == 0:
            return 0.0
        return self.valid_bars / self.total_bars


def validate_bars(bars: List[MarketBar]) -> QualityReport:
    """Validate a list of MarketBar for OHLCV integrity."""
    if not bars:
        return QualityReport(
            symbol="", timeframe="", total_bars=0,
            valid_bars=0, invalid_bars=0, issues=["empty_bars"],
        )

    issues: List[str] = []
    valid = 0
    invalid = 0

    for i, bar in enumerate(bars):
        bar_issues = _check_bar(bar, i)
        if bar_issues:
            invalid += 1
            issues.extend(bar_issues)
        else:
            valid += 1

    return QualityReport(
        symbol=bars[0].symbol,
        timeframe=bars[0].timeframe,
        total_bars=len(bars),
        valid_bars=valid,
        invalid_bars=invalid,
        issues=issues,
    )


def _check_bar(bar: MarketBar, index: int) -> List[str]:
    """Check a single bar for issues."""
    issues: List[str] = []

    # Non-positive price
    if bar.open <= 0:
        issues.append(f"bar[{index}]:open<=0")
    if bar.high <= 0:
        issues.append(f"bar[{index}]:high<=0")
    if bar.low <= 0:
        issues.append(f"bar[{index}]:low<=0")
    if bar.close <= 0:
        issues.append(f"bar[{index}]:close<=0")

    # Negative volume
    if bar.volume < 0:
        issues.append(f"bar[{index}]:volume<0")

    # High < low
    if bar.high < bar.low:
        issues.append(f"bar[{index}]:high<low")

    # Open/close outside [low, high]
    if bar.open > bar.high:
        issues.append(f"bar[{index}]:open>high")
    if bar.open < bar.low:
        issues.append(f"bar[{index}]:open<low")
    if bar.close > bar.high:
        issues.append(f"bar[{index}]:close>high")
    if bar.close < bar.low:
        issues.append(f"bar[{index}]:close<low")

    return issues
