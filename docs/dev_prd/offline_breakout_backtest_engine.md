# Offline Breakout Backtest Engine — Design Document

## Signal Rules

The breakout signal engine detects price breakouts with volume confirmation.

### Upside Breakout (LONG)
1. Current close > rolling_high * (1 + breakout_threshold)
2. Current volume >= avg_volume * volume_multiplier
3. Entry at close price
4. Stop at close - (ATR * stop_atr_multiplier)
5. Take profit at close + reward_distance

### Downside Breakout (SHORT)
1. Current close < rolling_low * (1 - breakout_threshold)
2. Current volume >= avg_volume * volume_multiplier
3. Entry at close price
4. Stop at close + (ATR * stop_atr_multiplier)
5. Take profit at close - reward_distance

### Parameters
```python
BreakoutSignalParams:
    lookback: int = 20              # Rolling window for high/low
    breakout_threshold: float = 0.005  # 0.5% beyond rolling level
    volume_multiplier: float = 1.5   # Volume must be 1.5x average
    min_bars_required: int = 30      # Need at least 30 bars
    cooldown_bars: int = 3           # No signals for 3 bars after entry
    stop_atr_multiplier: float = 1.5 # Stop = ATR * 1.5
    take_profit_rr: float = 2.0      # TP = 2R reward
```

## Trade Simulation Model

### Entry
- Signal detected at bar index `i`
- Entry at close price of bar `i`
- Slippage applied: `entry * (1 +/- slippage_pct)`

### Exit Logic (in priority order)
1. **Stop Loss**: If high/low touches stop price → exit at stop
2. **Take Profit**: If high/low touches TP price → exit at TP
3. **Max Hold**: If held for `max_hold_bars` → exit at market
4. **End of Data**: If data runs out → exit at last close

### Slippage Model
- Default: 0.05% (5 basis points)
- Applied to entry price (adverse direction)
- Applied to exit price (adverse direction for stop/TP fills)

### Fee Model
- Default: 0.1% (10 basis points)
- Applied to both entry and exit notional
- `fees = (entry_price + exit_price) * fee_pct`

### R-Multiple Calculation
```
risk_distance = |entry_price - stop_price|
realized_r = net_pnl / risk_distance
net_pnl = gross_pnl - fees - slippage_cost
```

## Risk Model

### Position Sizing
- Fixed R per trade (default 1.0R)
- No compounding in offline mode
- Risk is expressed in R-multiples for comparability

### MFE/MAE Tracking
- **MFE (Maximum Favorable Excursion)**: Best unrealized profit in R
- **MAE (Maximum Adverse Excursion)**: Worst unrealized loss in R
- Tracked per bar during the trade lifecycle

### Quality Metrics
- **Quality Adjusted Score**: `expectancy * sqrt(trade_count) * win_rate`
- **Sample Adequacy**: `min(1.0, trade_count / 30.0)`
- **Profit Factor**: `gross_wins / abs(gross_losses)`

## Trade Outcome Data Model

```python
@dataclass(frozen=True)
class TradeOutcome:
    trade_id: str
    signal_id: str
    entry_bar_index: int
    exit_bar_index: int
    entry_price: float
    exit_price: float
    exit_reason: str       # TAKE_PROFIT, STOP_LOSS, MAX_HOLD, END_OF_DATA
    realized_r: float
    gross_pnl: float
    fees: float
    slippage_cost: float
    net_pnl: float
    mfe_r: float
    mae_r: float
    hold_bars: int
```

## Metrics Computation

Per-run metrics:
- `trade_count`, `win_rate`, `expectancy_r`, `avg_r`, `median_r`
- `max_drawdown_r`, `profit_factor`
- `avg_mfe_r`, `avg_mae_r`
- `exposure_bars`, `avg_hold_bars`
- `quality_adjusted_score`, `sample_adequacy_score`

Aggregate metrics:
- Weighted averages across runs
- Worst drawdown across all runs
- Median expectancy across runs
