# Quant System Current Status — 2026-08-07

## Repository baseline

- Primary GitHub repository: `badyhz/qq`
- Default branch: `main`
- GitHub is the primary development baseline.
- Production remains a separate deployment boundary and must not be changed merely because GitHub code is ready.

Current relevant GitHub state:

```text
P1-03 weak-short assumptions builder merged to main:
984808e4b328adb892a022ac7235efe4699f7930
```

## Current maturity

```text
READINESS_STATUS: READY_FOR_HUMAN_REVIEW
CURRENT_SYSTEM_LEVEL: LEVEL_2
CURRENT_STATUS: READY_FOR_P1_03_ASSUMPTIONS_REVIEW
```

Latest verified production evidence state on 2026-08-07:

- Continuous observation: 17 calendar days.
- Universe: 8 symbols.
- Valid book snapshots: 368 per symbol.
- Valid depth snapshots: 363–367 per symbol.
- Funding: 51 continuous windows per symbol.
- Prospective stops: 439.
- Gap-through stops: 28.
- Prospective gap coverage: 100%.
- Historical overlap: 200.
- Duplicate OPEN: 0.
- Duplicate signal: 0.
- P1-03 assumptions approved: false.
- Net-friction cohort active: false.
- P1-03 trusted closed: 0.

Production continues Shadow-only operation.

## Safety / activation state

```text
P1_03_ASSUMPTIONS_APPROVED: NO
P1_03_NET_CONFIG_PRODUCTION: UNCONFIGURED
P1_03_COHORT_ACTIVE: NO
TESTNET: NO
LIVE: NO
REAL_ORDERS: NO
```

Level 2 confirms evidence maturity only. It does not authorize Testnet, Live, real orders, or automatic cohort activation.

## Independent Console defect

The known isolated read-only Console count defect remains a separate engineering item:

```text
canonical OPEN:             10
registry OPEN:              10
Console current_positions:  10 rows
Console open_positions:     0  # incorrect scalar
```

Root cause is known in `scripts/generate_static_console.py`: the positions list comes from canonical OPEN population while the scalar reads `scorecard.global_metrics.open_positions`.

This defect does not invalidate Level 2 evidence maturity or the weak-short research result. It should be fixed independently with a canonical-source regression test.

## Indicator research — standalone entry track closed

The 2026-08-07 indicator strategy research has been completed and intentionally stopped to avoid parameter rescue / data mining.

Final standalone-entry conclusions:

```text
BOTTOM_TREASURE_LONG = REJECT_FOR_SHADOW
IRON_TOP_SHORT_ENTRY = REJECT_FOR_SHADOW
MARKET_ACCELERATOR_LONG = REJECT_FOR_SHADOW
MARKET_ACCELERATOR_SHORT_FIXED_2R = REJECT_FOR_SHADOW
MARKET_ACCELERATOR_SHORT_LIFECYCLE = REJECT_FOR_SHADOW
MARKET_ACCELERATOR_FAST_SHORT = REJECT_FOR_SHADOW
STANDALONE_INDICATOR_ENTRY_RESEARCH = COMPLETE
NEW_INDICATOR_COHORT = NO
```

The indicators were also tested as isolated entry filters on the existing strategies. They did not improve the aggregate MACD or weak-short baseline enough to justify production integration.

Reusable indicator formulas / public-history tooling may remain available for research, risk or exit analysis, but they are not an approved automatic-entry strategy.

## Existing strategy research — weak_short_watch promoted as the main candidate

The existing `weak_short_watch` strategy, without the new indicator overlays, is currently the strongest research candidate.

Universe:

```text
XRPUSDT / ARBUSDT / DOGEUSDT
15m / 1h
SHORT
```

Discovery / recent-year validation:

```text
2025-08 .. 2026-07
4,534 trades
PF 1.1275
Expectancy +0.0811R
6/6 symbol×timeframe series positive expectancy
```

Untouched older-year holdout:

```text
2024-08 .. 2025-07
4,483 trades
PF 1.0904
Expectancy +0.0583R
6/6 symbol×timeframe series positive expectancy
```

Older-year time split:

```text
first half  PF 1.030  / Exp +0.0197R
second half PF 1.151  / Exp +0.0951R
```

A small research-only 0.5 bp/side fee stress still kept the older-year aggregate positive, but that stress is not the P1-03 authority model.

Current research classification:

```text
WEAK_SHORT_EXISTING_BASELINE = RESEARCH_HOLDOUT_PASS
```

This is not Testnet authorization. The next authority is P1-03 net-friction review.

## Human-confirmed Binance USD-M fee evidence

On 2026-08-07 the user supplied a Binance USD-M fee screen showing the regular-user schedule:

```text
USDT maker: 0.0200% = 2 bp
USDT taker: 0.0500% = 5 bp
BNB-discount maker: 0.0180% = 1.8 bp
BNB-discount taker: 0.0450% = 4.5 bp
```

For the primary P1-03 weak-short proposal use the conservative assumption:

```text
entry_fee_liquidity = TAKER
exit_fee_liquidity = TAKER
entry_fee_bps = 5
exit_fee_bps = 5
fee_rate_source = HUMAN_CONFIRMED_BINANCE_USDM_REGULAR_USER_FEE_SCREEN_2026_08_07
```

Do not assume the 4.5 bp BNB discount unless BNB fee-payment eligibility is separately confirmed. The discounted rate may be used only as a secondary sensitivity scenario.

## P1-03 weak-short assumptions proposal builder

Merged to main in commit:

```text
984808e4b328adb892a022ac7235efe4699f7930
```

Files:

```text
scripts/build_p1_03_weak_short_assumptions_package.py
tests/unit/test_build_p1_03_weak_short_assumptions_package.py
```

Focused verification before merge included the existing authoritative net-friction contract:

```text
135 passed
0 failed
```

The builder does not modify strategy state, ledgers, manifests, deployment, cohort activation, Testnet, Live or orders.

Frozen evidence policy:

- spread = per-symbol p95 one-leg adverse spread;
- SHORT entry slippage = p90 SELL book impact;
- SHORT exit slippage = p90 BUY book impact;
- funding = `OBSERVED_EVENTS`;
- stop gap execution = `OBSERVED_FIRST_EXECUTABLE`;
- notional candidates = 1000 / 5000 / 10000 USDT;
- exact symbol profiles = XRPUSDT / ARBUSDT / DOGEUSDT;
- generated assumptions pass through the existing `validate_assumptions_for_activation()` contract;
- each valid candidate receives a deterministic assumptions hash;
- result can only become `READY_FOR_HUMAN_ASSUMPTIONS_REVIEW`, never automatically approved.

## Next exact operation — read-only runtime package generation

GitHub intentionally does not contain production runtime evidence such as:

```text
/opt/quant-shadow/qq/reports/strategies/friction_evidence_readiness.json
```

That runtime file contains the mature XRP/ARB/DOGE p95 spread and p90 buy/sell book-impact values needed to build the real candidate package.

Do **not** update the production worktree merely to run this review tool. Use a temporary clean GitHub checkout and read the production readiness file read-only.

Recommended server-side review procedure:

```bash
rm -rf /tmp/qq-p1-03-review
git clone --quiet https://github.com/badyhz/qq.git /tmp/qq-p1-03-review
cd /tmp/qq-p1-03-review
git checkout --quiet 984808e4b328adb892a022ac7235efe4699f7930

python3 scripts/build_p1_03_weak_short_assumptions_package.py \
  --readiness /opt/quant-shadow/qq/reports/strategies/friction_evidence_readiness.json \
  --output /tmp/p1_03_weak_short_assumptions_package.json \
  --entry-fee-bps 5 \
  --exit-fee-bps 5 \
  --entry-fee-liquidity TAKER \
  --exit-fee-liquidity TAKER \
  --fee-rate-source HUMAN_CONFIRMED_BINANCE_USDM_REGULAR_USER_FEE_SCREEN_2026_08_07
```

Expected successful review-only result:

```text
package_status = READY_FOR_HUMAN_ASSUMPTIONS_REVIEW
candidate_count = 3
cohort_activation_performed = false
```

The output file must remain a review artifact until its values, notional boundary and assumptions hash are explicitly approved. Generating the package does not authorize copying it into production config or activating the net-friction cohort.

## Correct next sequence

```text
1. Generate weak-short P1-03 candidate package from mature runtime readiness evidence.
2. Compare 1000 / 5000 / 10000 USDT candidates and inspect XRP/ARB/DOGE spread/slippage values.
3. Human-select one supported notional boundary and approve/reject the exact assumptions hash.
4. Only after explicit approval: prepare a separate deployment/activation change.
5. Only after separate activation authorization: start prospective trusted net-friction cohort.
6. Accumulate trusted Net PF / Net Expectancy sample.
7. Decide whether Testnet deserves a separate review.
```

No step above implies automatic progression to Testnet or Live.

## GitHub-first development rule

From this point forward, `badyhz/qq` is the primary development baseline unless a task explicitly targets another repository.

Working rules:

- inspect current GitHub state before editing;
- make focused changes instead of broad rewrites;
- keep strategy cohorts and evidence populations isolated;
- add or update tests with code changes;
- keep Testnet / Live / real-order activation behind explicit human authorization;
- do not modify production state merely because GitHub code changes are ready;
- preserve small, auditable commits and avoid unrelated generated-file sprawl;
- temporary research workflows/scripts must be removed or closed when their research question is resolved.

## Status summary

```text
SYSTEM_LEVEL = LEVEL_2
EVIDENCE_GATE = MATURE
WEAK_SHORT_RESEARCH = HOLDOUT_PASS
INDICATOR_STANDALONE_ENTRY = REJECTED / CLOSED
P1_03_PROPOSAL_BUILDER = MERGED_TO_MAIN
P1_03_PRIMARY_FEE_INPUT = TAKER 5 BP / SIDE
P1_03_RUNTIME_PACKAGE = PENDING_READ_ONLY_GENERATION
P1_03_ASSUMPTIONS_APPROVED = NO
P1_03_COHORT_ACTIVE = NO
CONSOLE_OPEN_COUNT = KNOWN_ISOLATED_DEFECT
TESTNET/LIVE/REAL_ORDER = DISABLED
GITHUB = PRIMARY DEVELOPMENT BASELINE
```