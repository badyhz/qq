# Quant System Current Status — 2026-08-07

## Repository baseline

- Primary GitHub repository: `badyhz/qq`
- Default branch: `main`
- GitHub main head before this status sync: `ebc50992f63f745a78742e2b65142af23b6343d0`
- The latest code commit before this sync was dated 2026-07-23.
- Production evidence continued accumulating after that date; this document records the 2026-08-06 Level 2 maturity result so GitHub remains an authoritative development handoff point.

## Current maturity

```text
READINESS_STATUS: READY_FOR_HUMAN_REVIEW
CURRENT_SYSTEM_LEVEL: LEVEL_2
CURRENT_STATUS: READY_FOR_P1_03_ASSUMPTIONS_REVIEW
```

Evidence Gate maturity confirmed on 2026-08-06:

- Continuous observation: 16 calendar days (requirement: 14+).
- Universe: 8 symbols.
- Valid book snapshots: 349 per symbol.
- Valid depth snapshots: at least 346 per symbol.
- Funding: 48 consecutive windows per symbol; missing = 0; true conflicts = 0.
- Prospective stops: 418; gap coverage = 100%.
- Natural pipeline runs: 347 / 347 successful; pipeline failures = 0; missing = 0.
- Historical overlap: 200.
- Duplicate OPEN = 0.
- Duplicate signal = 0.

## Safety / activation state

```text
P1_03_CONFIGURED: NO
P1_03_ACTIVE: NO
TESTNET: NO
LIVE: NO
REAL_ORDERS: NO
```

Level 2 confirms evidence maturity only. It does not authorize Testnet, Live, real orders, or automatic cohort activation.

## Independent Console defect

The 2026-08-06 re-audit found an isolated read-only Console count defect:

```text
canonical OPEN:             10
registry OPEN:              10
Console current_positions:  10 rows
Console open_positions:     0  # incorrect scalar
```

This does not invalidate the Level 2 evidence Gate.

GitHub code inspection on 2026-08-07 identified the likely root cause in `scripts/generate_static_console.py`:

- the open-position table / `current_positions` is derived from canonical records in `bundle["all_canonical"]`;
- the headline `open_positions` scalar is derived from `scorecard.global_metrics.open_positions`;
- these two sources can diverge, producing the observed `10 rows / 0 scalar` mismatch.

Required fix is intentionally independent from P1-03 assumptions approval. The scalar should be derived from the same canonical OPEN population used to render current positions, with regression coverage that fails on source divergence.

## Next workstreams

### A. Console scalar repair

Minimal isolated repair only:

1. derive `open_positions` from canonical OPEN positions;
2. use the same value in HTML and public JSON;
3. add regression coverage for canonical OPEN > scorecard scalar;
4. do not change trading state, positions, P1-03, timers, or production data.

### B. P1-03 assumptions review

Prepare a human-review assumptions package covering fee, spread/slippage, funding, gap/stop handling, notional mapping, cohort scope, stop/rollback conditions, and trusted-net review thresholds.

Approval of assumptions must remain separate from deployment and cohort activation.

### C. Indicator-composite strategy track

A new strategy track may proceed independently of the existing MACD / weak-short cohort.

Initial composition:

- Bottom Treasure (`底部寻宝`): long-entry candidate.
- Market Accelerator / 疾速500: acceleration regime / no-chase filter.
- Iron Top Critical (`铁顶临界`): long exit / reduction signal; later short candidate.
- Order-flow indicator: optional confirmation layer after the first version is testable.

The first implementation must explicitly define entry, exit, stop, take-profit, sizing, duplicate-signal handling, cooldown, max concurrent positions, loss-pause rules, timeframe, universe, and friction assumptions before any order integration.

This new strategy must have an independent cohort, independent backtest/shadow statistics, and must not contaminate the existing Level 2 evidence population.

## GitHub-first development rule

From this point forward, `badyhz/qq` is the primary development baseline for the quant system unless a task explicitly targets another repository.

Working rules:

- inspect current GitHub state before editing;
- make focused changes instead of broad rewrites;
- keep strategy cohorts and evidence populations isolated;
- add or update tests with code changes;
- keep Testnet / Live / real-order activation behind explicit human authorization;
- do not modify production state merely because GitHub code changes are ready;
- preserve small, auditable commits and avoid unrelated generated-file sprawl.

## Status summary

```text
SYSTEM_LEVEL = LEVEL_2
EVIDENCE_GATE = MATURE
P1_03 = READY_FOR_ASSUMPTIONS_REVIEW, NOT ACTIVE
CONSOLE_OPEN_COUNT = KNOWN_ISOLATED_DEFECT
NEW_INDICATOR_STRATEGY = READY_FOR STRATEGY SPEC + IMPLEMENTATION
TESTNET/LIVE/REAL_ORDER = DISABLED
GITHUB = PRIMARY DEVELOPMENT BASELINE
```
