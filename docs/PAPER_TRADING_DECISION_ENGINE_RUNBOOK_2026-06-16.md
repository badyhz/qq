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

### Daily ops (one-click)

```bash
python3 scripts/run_paper_daily_ops.py
```

Runs all paper runners (dry-run, multi-fixture, parameter sweep, ops report, runtime) in sequence.
Generates dashboard index. Outputs:
- `reports/paper_trading_daily_ops.json`
- `reports/paper_trading_daily_ops.md`
- `reports/paper_trading_index.html`

### Acceptance suite

```bash
python3 scripts/run_paper_trading_acceptance_suite.py
```

Runs 27 checks: compileall, paper tests, dry-run, no-secrets, no-forbidden-imports,
human approval gate, core modules (22), fixtures, report, multi-fixture runner, security scan,
parameter sweep runner, ops report runner, scorecard module, reports generatable,
runtime config module, strategy registry module, runtime orchestrator module, runtime runner,
HTML dashboard module, run history module, dashboard index module, daily ops runner,
daily ops report, history file, dashboard index file.

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

### Run History (`core/paper_trading/run_history.py`)
JSONL append-only history of runtime runs. Supports: append_record, read_history (with limit),
filter_by_date, compare_last_two (trend delta), compute_trend (rising/falling/flat).
Default path: `reports/paper_trading_run_history.jsonl`.

### Dashboard Index (`core/paper_trading/dashboard_index.py`)
Scans reports directory for paper_trading .md and .html files. Generates self-contained
index HTML with report list, sizes, timestamps. No external resources.

### Review Queue (`core/paper_trading/review_queue.py`)
Local JSONL queue for operator review. Candidates have statuses:
- **PENDING_REVIEW** — Awaiting operator decision
- **WATCHLIST** — Interesting, observe further
- **REJECTED** — Does not meet criteria
- **EXPIRED** — Auto-expired after 24 hours
- **PAPER_APPROVED** — Paper review passed (NOT real orders)

Supports: append_candidate, read_queue (with status filter), read_pending,
mark_watchlist, mark_rejected, mark_paper_approved, expire_old, queue_summary.

### Candidate Ranker (`core/paper_trading/candidate_ranker.py`)
Scores and prioritizes review candidates. Output: HIGH / MEDIUM / LOW / REJECT priority.
Factors: strategy_score, rating, RR ratio, sample size, drawdown, profit factor, duplicate symbol.
A/B rating can reach HIGH/MEDIUM. C only LOW. D/REJECT always REJECT.

### Operator Decision Pack (`core/paper_trading/operator_decision_pack.py`)
Combines ranked candidates into a human-readable review package.
Outputs: dict, markdown, HTML. Includes: grouped candidates, risk explanations,
allowed actions (WATCHLIST / REJECTED / PAPER_APPROVED), safety declarations.

### Operator Review Runner (`scripts/run_paper_operator_review.py`)
One-command operator review: runs runtime → creates candidates → ranks → generates decision pack.
Outputs: JSON + Markdown + HTML + queue JSONL.

### Release Manifest (`core/paper_trading/release_manifest.py`)
Generates RC checklist: modules, scripts, fixtures, reports, safety flags, known limits, blockers.
`generate_manifest()` → dict. `manifest_ready()` → bool. `manifest_to_markdown()` → md.

### Artifact Validator (`core/paper_trading/artifact_validator.py`)
Validates local reports integrity: JSON parseable, JSONL line-by-line, Markdown non-empty,
HTML no external links/script src. `validate_artifacts(dir)` → list of issues.

### Release Candidate Runner (`scripts/run_paper_release_candidate.py`)
One-click full RC validation: runs all runners, generates manifest, validates artifacts.
Outputs: JSON + Markdown. Reports RC_READY status.

### How to Run Full Release Candidate

```bash
# Full RC validation (runs everything)
python3 scripts/run_paper_release_candidate.py

# Or step by step:
python3 scripts/run_paper_daily_ops.py
python3 scripts/run_paper_operator_review.py
python3 scripts/run_paper_trading_acceptance_suite.py

# View results
open reports/paper_trading_release_candidate.html
open reports/paper_trading_index.html
```

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
# One-click daily ops (runs all runners + operator review + generates index)
python3 scripts/run_paper_daily_ops.py

# Or individual runners:
python3 scripts/run_paper_runtime.py
python3 scripts/run_paper_parameter_sweep.py
python3 scripts/run_paper_trading_ops_report.py
python3 scripts/run_paper_operator_review.py

# View results
open reports/paper_trading_index.html
open reports/paper_trading_operator_review.html
open reports/paper_trading_dashboard.html
```

## Operator Review Workflow

After daily ops, the operator reviews candidates:

1. Open `reports/paper_trading_operator_review.html`
2. Review HIGH/MEDIUM priority candidates
3. For each candidate, decide:
   - **WATCHLIST** — Interesting, observe further
   - **REJECTED** — Does not meet criteria
   - **PAPER_APPROVED** — Paper review passed
4. PAPER_APPROVED does NOT create real orders — it's a paper-only review status

## Why Still Cannot Do Testnet/Live

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

## Round 8 Status

Round 8 is **Release Candidate 收口 only**. It includes:

- `release_manifest.py` — RC checklist (modules, scripts, fixtures, safety flags, known limits)
- `artifact_validator.py` — Validates local reports integrity
- `run_paper_release_candidate.py` — One-click full RC validation
- Extended acceptance suite with 48 checks

**Round 8 has NOT started Round 9.**

## Round 9: Readonly Data Source (NOT YET STARTED)

Round 9 will add a **data_source abstraction layer** for readonly real market data.

**Scope (when authorized):**
- `data_source` interface
- `fixture_adapter` (existing behavior)
- `public_market_snapshot_adapter` (new, REST only)
- Config switch: `data_source: fixture / live`
- Safety check: no secret, no order, no testnet/live

**Forbidden in Round 9:**
- WebSocket
- Account sync
- API keys
- .env
- Orders
- Testnet
- Live
- Complex scheduling

**Round 9 requires separate human authorization.**

## PHASE10_SHADOW_GATE.md (NOT YET CREATED)

`PHASE10_SHADOW_GATE.md` must be created **after Round 9** readonly data source is complete.

It will define:
- Shadow metrics (hit rate, false positive rate)
- Sample thresholds (>= 30 valid paper plans)
- HIGH/MEDIUM/LOW distribution requirements
- Expectancy/profit factor by priority level
- No-distinguishability investigation flow
- Pass/fail rules
- Shadow extension conditions
- Testnet/live prohibition gate

**Do NOT create PHASE10_SHADOW_GATE.md until Round 9 is complete.**

## How to Judge if System is RC-Ready

Run the release candidate runner:

```bash
python3 scripts/run_paper_release_candidate.py
```

Check output for:
- All runners PASS
- Manifest RC Ready: YES
- Artifact errors: 0
- Safety flags complete
- Known limits documented
- Next phase blockers documented

## Current Known Limits

- **Fixture-only** — No live market data
- **Single symbol** — Each replay runs one fixture at a time
- **No persistence** — Ledger and account state are in-memory only
- **No execution** — Plans never become real orders
- **No network** — Zero HTTP calls, zero webhooks
- **No testnet** — Testnet not implemented
- **No live** — Live trading not implemented
- **No data_source** — Round 9 not started
- **No Shadow Gate** — PHASE10_SHADOW_GATE.md not created

## Next Phase Blockers

Before testnet, ALL of these must be completed:

1. **Round 9** — Readonly data source (separate authorization required)
2. **Shadow period** — 14 days real market data paper shadow
3. **PHASE10_SHADOW_GATE.md** — Define shadow metrics and pass/fail criteria
4. **Shadow validation** — 30+ valid plans, HIGH > MEDIUM > LOW expectancy
5. **Testnet gate** — Separate authorization required
6. **Testnet shadow** — 3-7 days testnet order lifecycle validation
7. **Live gate** — Separate authorization required, 2-3 weeks minimum

## Safety

- Testnet/live: **STILL PROHIBITED**
- Real orders: **STILL PROHIBITED**
- Secret reads: **STILL PROHIBITED**
- Network calls: **STILL PROHIBITED**
- Round 9 data_source: **NOT YET STARTED**
- PHASE10_SHADOW_GATE.md: **NOT YET CREATED**
