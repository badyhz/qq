# Trading Rules

## Current Phase: Skeleton Stage

This file defines trading principles that apply once trading logic is implemented.
Current state: Stage 0 - dry-run only, no real trading logic implemented.

## Hard Constraints (Active Now)

### 1. Dry-Run Only
- **NEVER** execute real orders without explicit permission
- All trading features must work in dry-run mode first
- Dry-run execution is the default and only mode currently

### 2. Implementation Principles
- Trading logic must be testable in dry-run mode
- All parameters must be configurable (no magic numbers in code)
- Signal generation must be deterministic for testing

## Future Principles (Not Yet Implemented)

### Signal Generation (To be defined when R8-R11 complete)
- Signals must be deterministic for backtesting
- All indicators must be documented with formulas
- Signal strength must be quantifiable
- Multi-timeframe confirmation required for entry

### Order Execution (To be defined when R11 complete)
- All order paths must be testable with mock data
- Simulate order latency in dry-run
- Simulate slippage in dry-run
- Simulate fee calculation in dry-run

### Position Management (To be defined when risk_manager implemented)
- Maximum position size: defined in config
- Position limits per symbol: defined in config
- Risk per trade: defined in config
- Maximum concurrent positions: defined in config

### Risk Management (To be defined when R11-R13 complete)
- Stop loss is mandatory for every position
- Stop loss level: defined in config
- Take profit level: defined in config
- All risk limits must be configurable

## Implementation Checklist

When implementing trading features, ensure:
- [ ] Feature works in dry-run mode
- [ ] All parameters are in config.yaml
- [ ] No hardcoded trading parameters
- [ ] Logic is testable with mock data
- [ ] Error paths are tested
- [ ] Documentation includes formulas and formulas

## Reference

See PROJECT_STATE.md for current phase constraints
See TASKS.md for implementation roadmap
