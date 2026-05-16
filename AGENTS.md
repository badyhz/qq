# Codex Project Control

## Project Overview

This is a quantitative trading system for Binance, currently in initialization phase.

**Current State:** Stage 0 - Project Skeleton
**Default Mode:** dry-run (no real trading)

## Critical Context

### Project Goals
1. Build a runnable Python quantitative system skeleton
2. Default dry-run mode - no real orders
3. Target exchange: Binance
4. Priorities: structure clarity, testability, risk control

### Project Structure
```
qq/
├── main.py              - Entry point
├── config.yaml          - Configuration
├── requirements.txt     - Dependencies
├── core/                 - Core modules
│   ├── data_feed.py     - Market data
│   ├── signal_engine.py - Signal generation
│   ├── risk_manager.py  - Risk management
│   ├── execution.py     - Order execution
│   ├── order_manager.py - Order tracking
│   └── trade_logger.py  - Trade logging
├── utils/                - Utilities
│   ├── config_loader.py - Config management
│   ├── logger.py        - Logging system
│   └── helpers.py       - Helper functions
└── logs/                 - Log files
```

### Control Files
- `PROJECT_STATE.md` - Project state tracking
- `TASKS.md` - Task queue and acceptance criteria
- `acceptance.json` - Validation rules and milestones
- `feature_list.json` - Feature completion status
- `AGENT_RULES.md` - Agent behavior rules

## Safety Rules

### Hard Constraints
- **NO real orders** without explicit permission
- **NO hardcoded secrets** - use environment variables only
- **Always default to dry-run mode**
- **All trading logic must be testable in dry-run**

### Required Reading Order
Before making any changes, read in order:
1. PROJECT_STATE.md
2. TASKS.md
3. acceptance.json
4. feature_list.json
5. AGENT_RULES.md

## Development Workflow

### Task Execution
1. Read current state from control files
2. Identify next task from TASKS.md
3. Implement with module separation
4. Test in dry-run mode
5. Update control files
6. Document changes

### Acceptance Criteria
- Task must be runnable
- Task must be testable
- Dry-run mode must work
- Changes must be documented

## Quick Commands

```bash
# Run dry-run mode (default)
python3 main.py

# Run with max loops
QQ_MAX_LOOPS=10 python3 main.py

# Run with custom interval
QQ_LOOP_INTERVAL=2 QQ_MAX_LOOPS=5 python3 main.py

# Using start script
./start.sh
```

## Key Reminders

- This is a trading system - assume errors can lose money
- Always test in dry-run before suggesting live mode
- Check PROJECT_STATE.md for current constraints
- Follow AGENT_RULES.md for all development
