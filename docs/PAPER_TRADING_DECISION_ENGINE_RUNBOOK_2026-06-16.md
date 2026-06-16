# Paper Trading Decision Engine Runbook

**Date:** 2026-06-16
**Status:** Paper-only / local / no network / no real orders

## What It Does

The paper trading decision engine simulates a trading loop locally:

1. **Signal generation** — MACD rebound signal on K-line fixtures
2. **Order planning** — Converts signals to `OrderPlan` with entry, SL, TP
3. **Risk sizing** — Position sizing, RR ratio validation, margin cap
4. **Exit rules** — Priority: invalidation > stop_loss > trailing > time > take_profit
5. **Replay engine** — Processes K-line bars, manages active plans
6. **Paper ledger** — Tracks PnL, win_rate, drawdown, exit distribution
7. **Alert explainer** — Generates alert text (no webhook)
8. **Human approval gate** — Never auto-approves real orders
9. **Account state** — Balance, margin, daily loss, cooldown tracking
10. **Portfolio risk** — Max plans, symbol limits, direction blocks

## How to Run

### Dry-run runner

```bash
python3 scripts/run_paper_trading_decision_engine_dry.py
```

Outputs:
- Console summary
- `reports/paper_trading_decision_engine_report.md`
- `reports/paper_trading_decision_engine_summary.json`

### Multi-fixture replay runner

```bash
python3 scripts/run_paper_multi_fixture_replay.py
```

Runs all fixtures from `tests/fixtures/paper_trading/` through the MACD rebound signal.
Outputs:
- `reports/paper_trading_multi_fixture_summary.json`
- `reports/paper_trading_multi_fixture_report.md`

### Parameter sweep

```bash
python3 scripts/run_paper_parameter_sweep.py
```

Runs 486 parameter combinations across all fixtures. Scores each by win_rate, profit_factor,
expectancy, drawdown. Outputs:
- `reports/paper_trading_parameter_sweep.json`
- `reports/paper_trading_parameter_sweep.md`

### Ops report

```bash
python3 scripts/run_paper_trading_ops_report.py
```

Aggregates dry-run, multi-fixture, and parameter sweep into one ops report.
Outputs:
- `reports/paper_trading_ops_report.json`
- `reports/paper_trading_ops_report.md`

### Paper runtime

```bash
python3 scripts/run_paper_runtime.py
```

One-command full paper runtime: loads fixtures, runs strategy, computes metrics,
scorecard, alerts. Outputs:
- `reports/paper_trading_runtime_result.json`
- `reports/paper_trading_runtime_report.md`

With custom config:
```bash
python3 scripts/run_paper_runtime.py --config tests/fixtures/paper_trading/runtime_config_sample.json
```

### Acceptance suite

```bash
python3 scripts/run_paper_trading_acceptance_suite.py
```

Runs 21 checks: compileall, paper tests, dry-run, no-secrets, no-forbidden-imports,
human approval gate, core modules, fixtures, report, multi-fixture runner, security scan,
parameter sweep runner, ops report runner, scorecard module, reports generatable,
runtime config module, strategy registry module, runtime orchestrator module, runtime runner,
HTML dashboard module.

### Unit tests

```bash
python3 -m pytest tests/unit/ -k "paper or signal_to_plan or human_approval" -v
```

### Security scan

```bash
python3 -m pytest tests/unit/test_paper_security_scan.py -v
```

Static analysis: no HTTP, no forbidden imports, no secrets, no subprocess, no socket.

## How to Read Reports

The markdown report includes:
- Replay results (bars, signals, plans, trades)
- Ledger summary (win_rate, pnl, drawdown, exit_reasons)
- Performance metrics (profit_factor, expectancy, avg_win, avg_loss, consecutive_losses)
- Alerts (local alert bridge — INFO/WARNING/CRITICAL)
- Safety footer (NO_REAL_ORDER, NO_REAL_HTTP, etc.)

The JSON summary has the same data in machine-readable format.

## Key Modules

### Performance Metrics (`core/paper_trading/performance_metrics.py`)
Computes from PaperLedger: win_rate, profit_factor, expectancy, avg_win, avg_loss,
avg_rr_actual, max_drawdown, max_consecutive_losses.

### Local Alert Bridge (`core/paper_trading/local_alert_bridge.py`)
In-memory alert queue with INFO/WARNING/CRITICAL levels. No network, no persistence.
Use `push()`, `drain()`, `peek()`, `has_critical()`.

### Runtime Config (`core/paper_trading/runtime_config.py`)
Paper-only configuration: strategy_name, fixture_paths, risk params, alert flags.
Supports JSON loading, default config, validation. Mode must be "paper_only".

### Strategy Registry (`core/paper_trading/strategy_registry.py`)
Local strategy lookup. Built-in: macd_rebound. No dynamic imports, no network.
Register custom strategies with `registry.register(name, signal_fn, meta)`.

### Runtime Orchestrator (`core/paper_trading/runtime_orchestrator.py`)
Full pipeline: config + registry → fixtures → replay → metrics → scorecard → alerts.
Returns `RuntimeResult` with all stats, score, rating, safety flags.

### HTML Dashboard (`core/paper_trading/html_dashboard.py`)
Self-contained inline-CSS HTML report from RuntimeResult. No CDN, no external links.

### Strategy Scorecard (`core/paper_trading/strategy_scorecard.py`)
Rates strategy quality A/B/C/D/REJECT based on performance metrics.
Factors: win_rate, profit_factor, drawdown, expectancy, trade count, stability.
Small samples capped at B. Negative expectancy → C/D/REJECT.

### Risk Explainer (`core/paper_trading/risk_explainer.py`)
Human-readable explanations for rejection reasons: RR_TOO_LOW, MAX_OPEN_PLANS,
MAX_TOTAL_EXPOSURE, DUPLICATE_SYMBOL_DIRECTION, MAX_DAILY_LOSS, CONSECUTIVE_LOSS_COOLDOWN,
MALFORMED_FIXTURE, NO_SIGNAL.

### Fixture Validation
Empty and malformed fixtures are tested in `test_paper_fixture_validation.py`.
Empty arrays produce zero-bar replays. Malformed data raises ValueError/TypeError.

## Current Limitations

- **Fixture-only** — Uses local JSON fixtures, no live market data
- **Single symbol** — Each replay runs one fixture at a time
- **No persistence** — Ledger and account state are in-memory only
- **No execution** — Plans never become real orders
- **No network** — Zero HTTP calls, zero webhooks

## What It Cannot Do

- Connect to Binance or any exchange
- Place real or testnet orders
- Read API keys or secrets
- Send alerts to external services
- Access live market data

## How to Interpret Rating

| Rating | Score Range | Meaning |
|--------|-----------|---------|
| A | 75+ | Strong strategy, good for further testing |
| B | 55-74 | Decent strategy, needs more samples |
| C | 35-54 | Marginal, review parameters |
| D | 20-34 | Weak, likely unprofitable |
| REJECT | <20 | Do not use |

Small samples (<5 trades) are capped at B. Negative expectancy → C/D/REJECT.

## How to Do a Daily Paper Run

```bash
# Quick check
python3 scripts/run_paper_runtime.py

# Full analysis
python3 scripts/run_paper_parameter_sweep.py
python3 scripts/run_paper_trading_ops_report.py

# View results
open reports/paper_trading_dashboard.html
```

## How to Judge if Strategy Can Advance

Before considering testnet, ALL of these must be true:

1. **Scorecard rating A or B** — Strategy quality must be high
2. **Sufficient samples** — At least 20 trades across multiple fixtures
3. **Positive expectancy** — Expected value per trade > 0
4. **Controlled drawdown** — Max drawdown < 5% of equity
5. **Stable win rate** — Win rate > 50% with good RR
6. **No critical alerts** — No consecutive loss cooldowns or daily loss hits
7. **Parameter robustness** — Top parameter sets perform consistently across fixtures
8. **Human approval** — Explicit operator sign-off required

## Why Still Cannot Do Testnet/Live

- **No real market data** — Fixtures are synthetic/historical, not live feeds
- **No slippage modeling** — Real fills differ from paper fills
- **No latency simulation** — Real execution has delays
- **No exchange edge cases** — Rate limits, partial fills, disconnections
- **No regulatory compliance** — KYC, tax reporting, jurisdiction rules
- **Safety gate not yet built** — No testnet/live transition guard exists
- **Human approval required** — Cannot proceed without explicit operator authorization

## Next Steps (Future)

1. **Paper alert integration** — Send alert text to local log or notification
2. **Simulated portfolio** — Multi-symbol portfolio tracking over time
3. **Testnet gate** — When ready, gate transitions to testnet with explicit approval
4. **Live gate** — Far future, requires human approval + safety review

## Safety

- Testnet/live: **STILL PROHIBITED**
- Real orders: **STILL PROHIBITED**
- Secret reads: **STILL PROHIBITED**
- Network calls: **STILL PROHIBITED**
