# Shadow Trading Daily Operator Runbook

## 1. System Boundary

Current system is strictly:

- Paper-only
- Shadow-only
- Public readonly market data (Binance public kline API)
- No order
- No testnet
- No live
- No account
- No secret
- No .env read
- No websocket
- No daemon / background runner

## 2. Daily Commands

### A. Discover new opportunities + update existing positions

```bash
python3 scripts/run_shadow_trading_lifecycle.py --allow-public-http
python3 scripts/run_sample_collection_gate.py
```

This runs the full 5-step pipeline:
1. Enabled strategies scan
2. Strategy trade intents
3. Paper position simulator (new + existing)
4. Legacy quarantine
5. Performance scorecard

### B. Only manage existing positions (no new scans)

```bash
python3 scripts/run_shadow_position_update_only.py --allow-public-http
python3 scripts/run_sample_collection_gate.py
```

This runs a 4-step pipeline:
1. Paper position simulator (update-only, no new positions)
2. Legacy quarantine
3. Performance scorecard
4. Sample collection gate

### C. Offline check (no network)

```bash
python3 scripts/run_shadow_trading_lifecycle.py --offline-sample
python3 scripts/run_shadow_position_update_only.py
python3 scripts/run_sample_collection_gate.py
```

### D. Check current status

```bash
python3 scripts/print_shadow_operator_status.py
```

## 3. Reports

After each run, check these reports:

```text
reports/strategies/YYYY-MM-DD_shadow_lifecycle_result.md
reports/strategies/YYYY-MM-DD_shadow_position_update_result.md
reports/strategies/YYYY-MM-DD_shadow_sample_gate.md
reports/strategies/YYYY-MM-DD_paper_performance_scorecard.md
```

## 4. Status Fields

### Pipeline level
- `pipeline_status`: PASS or FAIL — whether all steps completed
- `new_positions_count`: how many new positions opened (should be 0 in update-only)
- `existing_positions_count`: how many existing positions were processed
- `positions_updated_count`: how many received kline update
- `positions_skipped_no_future_bars`: no bars after opened_bar_time
- `positions_skipped_overlap_open`: blocked by overlap guard (same strategy+symbol+tf+side)

### Performance level
- `clean_positions`: positions not excluded by quarantine
- `closed_clean_positions`: clean positions that have closed (TP/SL/timeout)
- `excluded_positions`: legacy positions excluded from stats
- `sample_status`: INSUFFICIENT_CLOSED_SAMPLE / LOW_SAMPLE_SIZE / EVALUABLE

### Gate level
- `testnet_gate_status`: BLOCKED_INSUFFICIENT_CLOSED_SAMPLE / BLOCKED_LOW_SAMPLE_SIZE / PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW

## 5. Continue Shadow When

If any of these are true, continue shadow collection:

- `sample_status = INSUFFICIENT_CLOSED_SAMPLE`
- `testnet_gate_status = BLOCKED_INSUFFICIENT_CLOSED_SAMPLE`
- `closed_clean_positions < 10`

Action: keep running shadow lifecycle and update-only pipelines.

## 6. Human Review Gate

When `testnet_gate_status = PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW`, a human may review the data to decide next steps.

The system will NEVER claim testnet readiness or live readiness. The only gate output is `PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW`.

## 7. Common Mistakes

- **clean_positions increasing does not mean strategy is effective.** It means positions exist, not that they are profitable.
- **OPEN position != profit.** Only closed positions with TP count as wins.
- **closed_clean_positions too small to judge win rate.** Need at least 10 closed trades.
- **Repeated lifecycle should not re-open same position.** Overlap guard blocks same strategy+symbol+tf+side OPEN.
- **Update-only does not open new positions.** It only updates existing OPEN positions.
- **Legacy SL positions are excluded.** Quarantine tags pre-future-only positions; they don't count in performance stats.

## 8. Recommended Daily Rhythm

| Time | Action |
|------|--------|
| Morning | `run_shadow_trading_lifecycle --allow-public-http` + `run_sample_collection_gate` |
| Midday | `run_shadow_position_update_only --allow-public-http` + `run_sample_collection_gate` |
| Evening | `run_shadow_position_update_only --allow-public-http` + `run_sample_collection_gate` |
| Anytime | `print_shadow_operator_status` |

## 9. Safety Checklist

Before any run, verify:
- [ ] No API keys in environment
- [ ] No .env file loaded
- [ ] No testnet/live flags
- [ ] No order execution paths
- [ ] Public HTTP only (if using --allow-public-http)

## 10. File Inventory

| File | Purpose |
|------|---------|
| `scripts/run_shadow_trading_lifecycle.py` | Full pipeline: strategies → intents → positions → quarantine → scorecard |
| `scripts/run_shadow_position_update_only.py` | Update-only: positions → quarantine → scorecard (no new scans) |
| `scripts/run_sample_collection_gate.py` | Evaluate testnet readiness from registry |
| `scripts/print_shadow_operator_status.py` | Print current status summary |
| `core/paper_trading/paper_position_simulator.py` | Core simulation logic |
| `core/paper_trading/paper_performance_metrics.py` | Performance scoring |
| `core/paper_trading/shadow_run_registry.py` | Run tracking and gate evaluation |
