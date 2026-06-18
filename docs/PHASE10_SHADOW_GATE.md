# Phase 10 Shadow Gate — Real Market Paper Shadow Criteria

**Date:** 2026-06-16
**Status:** GATE_DEFINED
**Authorization:** Requires separate human approval before Phase 10 execution

## 1. Phase 10 Definition

Phase 10 is the **real market readonly paper shadow** phase.

- It is NOT testnet.
- It is NOT live.
- It does NOT allow orders.
- It does NOT allow account sync.
- It does NOT allow secret reads.
- It ONLY allows using readonly market data to generate paper-only plans and observation reports.

## 2. Runtime Period Thresholds

**Minimum runtime period:** 14 calendar days

**Minimum valid paper plans:** >= 30

If fewer than 30 valid plans are generated within 14 days, Phase 10 does NOT pass. Shadow must be extended.

### Valid Plan Definition

A valid plan must have:
- Signal generated
- Paper plan created
- RR meets threshold
- Not rejected by portfolio risk
- Entry/exit logic fully evaluable
- Has measurable outcome within evaluation window

### Invalid Plan Definition

Invalid plans include:
- Missing market data
- Invalid candle data
- Risk rejected
- Duplicate signal
- Cannot calculate RR
- Cannot calculate outcome

## 3. HIGH / MEDIUM / LOW Distribution Requirements

```
HIGH >= 5
MEDIUM >= 10
HIGH + MEDIUM >= 50% of valid plans
LOW <= 50% of valid plans
REJECT does not count as valid sample
```

If distribution is not satisfied:
- Cannot enter testnet
- Must continue shadow or adjust ranking logic and re-run

## 4. Hit and Failure Definitions

### Hit Definition

A trade is a hit when:
- Signal generated
- Paper plan created
- RR valid
- Entry condition satisfied
- Price reaches TP / trailing profit / defined positive outcome within N candles
- OR maintains valid structure without breaking invalidation before planned exit

### Failure Definition

A trade is a failure when:
- Price hits stop loss
- Invalidation level broken
- Timeout exit with negative expectancy
- Data invalid after signal
- Risk logic shows plan should not have been accepted

## 5. Core Performance Metrics

```
total expectancy > 0
HIGH expectancy > 0
profit factor > 1.2
HIGH profit factor preferably > 1.5
max drawdown within paper risk line
consecutive losses do not trigger severe circuit breaker
scorecard should not fall below B-/C+
```

## 6. Priority Level Effectiveness Requirements

```
HIGH expectancy > MEDIUM expectancy > LOW expectancy
HIGH profit factor > MEDIUM profit factor > LOW profit factor
HIGH max drawdown should not be materially worse than MEDIUM/LOW
```

If HIGH / MEDIUM / LOW performance is similar:
- Priority ranking is invalid
- Cannot enter testnet
- Must run no-distinguishability investigation

## 7. No-Distinguishability Investigation Flow

### Step 1: Check candidate_ranker weights
- Over-reliance on win_rate
- Weak small_sample_penalty
- Missing drawdown / RR / expectancy weight

### Step 2: Check strategy_scorecard
- Profit factor inflated by small samples
- drawdown_score too lenient
- expectancy_score too weak

### Step 3: Check RR thresholds
- min_rr_ratio too low
- Stop/take-profit distance distorted
- Trailing stop too optimistic

### Step 4: Check sample structure
- HIGH sample too small
- LOW dominates samples
- One or two symbols contribute most returns

### Step 5: Re-run shadow
- Small tuning: at least 7 more days
- Major tuning: restart 14-day shadow
- No direct testnet after tuning

## 8. System Stability Requirements

```
14 days without daily ops crash
daily report generated each day
operator review generated each day
data source remains readonly
0 secret reads
0 order path exposure
0 testnet/live calls
K-line parse success rate >= 98%
malformed data logged but does not crash system
```

## 9. Safety Red Lines

```
0 real orders
0 testnet orders
0 live orders
0 account sync
0 secret reads
0 .env reads
0 private endpoint calls
0 order_executor
0 websocket unless separately approved in future
0 deploy
0 push
```

## 10. Pass / Fail / Extend Rules

### PASS Conditions

All of the following must be true:
- 14 days completed
- >= 30 valid paper plans
- Sample distribution satisfied
- total expectancy > 0
- HIGH expectancy > 0
- profit factor > 1.2
- HIGH/MEDIUM/LOW ranking shows real distinction
- All safety red lines clean
- Daily stability clean

### FAIL Conditions

Any of the following triggers failure:
- expectancy <= 0
- profit factor <= 1.2
- HIGH does not outperform MEDIUM/LOW
- Safety red line violated
- Secret/order/testnet/live exposure
- System instability prevents daily evaluation

### EXTEND Conditions

Shadow may be extended if:
- Sample size insufficient
- Market regime too narrow
- Data gaps too large
- HIGH/MEDIUM sample count insufficient
- Metrics inconclusive

## 11. Phase 10 Output Artifacts

When Phase 10 execution completes, it must produce:
- Daily shadow reports
- Shadow ledger
- Operator review queue
- Valid plan sample table
- Priority-level performance report
- False positive report
- Risk rejection report
- Data quality report
- Final shadow gate result

## 12. Next Phase Gate

Phase 10 passing does NOT automatically enter testnet.

**Round 11 Testnet Gate** requires separate human approval.

Round 11 only allows:
- Testnet gate planning
- Dry gate design
- Testnet adapter skeleton

Real testnet order lifecycle requires separate approval after Round 11.

## Current Status

- Phase 10 execution: NOT STARTED
- Phase 10 shadow runtime: NOT STARTED
- Real market data: NOT CONNECTED
- PHASE10_SHADOW_GATE.md: CREATED (this document)
- Next action: AWAIT_HUMAN_APPROVAL for Phase 10 execution
