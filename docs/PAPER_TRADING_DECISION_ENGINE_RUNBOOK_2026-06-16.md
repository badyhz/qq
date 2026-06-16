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

### Acceptance suite

```bash
python3 scripts/run_paper_trading_acceptance_suite.py
```

Runs 12 checks: compileall, paper tests, dry-run, no-secrets scan, no-forbidden-imports,
human approval gate, core modules, planned modules, fixtures, report, multi-fixture runner,
security scan tests.

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
