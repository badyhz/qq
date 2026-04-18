# Codex Task: T202 Risk Manager Unit Tests

## Task ID
T202 - risk_manager.py 单元测试（最小版）

## Overview
为 `core/risk_manager.py` 添加单元测试，只覆盖权限检查和仓位计算逻辑。

---

## Step-by-Step Instructions

### Step 1: Read Source Code
First, read `core/risk_manager.py` to understand:
- The `RiskManager.__init__` constructor signature
- What config keys are used (look for `config.get(...)` calls)
- What `can_open_new_trade` method returns and what conditions it checks
- What `calculate_position` method returns and how it calculates quantities

### Step 2: Create Test File
Create `tests/unit/test_risk_manager.py` with following structure:

```python
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from core.risk_manager import RiskManager

# Fixtures will be added below

# Tests will be added below
```

### Step 3: Add Fixtures
Based on what you learned from reading `core/risk_manager.py` in Step 1, create these fixtures:

1. `mock_config()` - Return a config dict with:
   - `risk` section with keys used by RiskManager (starting_balance_usdt, risk_per_trade, max_daily_loss_pct, max_consecutive_losses, cooldown_minutes, min_notional_usdt, max_notional_usdt, leverage)
   - Any other keys constructor uses

2. `mock_logger()` - Return a MagicMock object

### Step 4: Test can_open_new_trade Permission Logic
Create test `test_can_open_new_trade`:

1. Test normal case - should return (True, "ok")
2. Test cooldown active - should return (False, "cooldown_active")
3. Test daily loss limit - should return (False, "daily_loss_limit")
4. Test consecutive losses limit - should return (False, "consecutive_loss_limit")
5. Test balance depleted - should return (False, "balance_depleted")

For each test case:
- Set up RiskManager with appropriate state
- Call `manager.can_open_new_trade(symbol, timestamp)`
- Assert the returned tuple matches expected (bool, reason)

### Step 5: Test calculate_position Logic
Create test `test_calculate_position`:

1. Test normal position calculation with valid parameters
2. Test adjustment for minimum notional
3. Test adjustment for maximum notional
4. Test handling of zero or negative risk distance

For each test case:
- Create a valid `signal` dict with entry, stop, tp
- Call `manager.calculate_position(signal, symbol, open_positions)`
- Assert returned quantity, notional, and other fields are correct

### Step 6: Verify Tests Run
Run: `pytest tests/unit/test_risk_manager.py -v`

---

## File Permissions

### Allowed to Modify/Create
- `tests/unit/test_risk_manager.py` - ONLY this file

### Forbidden to Modify (DO NOT TOUCH THESE FILES)
- `core/risk_manager.py`
- `main.py`
- `config.yaml`
- `core/execution.py`
- `core/order_manager.py`
- `core/signal_engine.py`
- `core/data_feed.py`
- `core/ticker_scanner.py`
- `core/trade_logger.py`
- `core/exchange.py`
- `utils/indicators.py`
- Any other files in `tests/` directory

---

## Important Instructions

1. **READ THE SOURCE FIRST** - Before writing any tests, read `core/risk_manager.py` carefully
2. **ADAPT TO SOURCE CODE** - Don't use hardcoded values. Use what the actual code expects.
3. **USE MAGICMOCK** - Mock logger dependency
4. **ONLY TEST TWO METHODS** - Test `can_open_new_trade` and `calculate_position` only
5. **DO NOT TEST on_trade_closed** - Not in scope for this task
6. **KEEP IT SIMPLE** - Only test specified scenarios

---

## Verification Commands

```bash
# Collect tests
pytest tests/unit/test_risk_manager.py --collect-only

# Run all tests
pytest tests/unit/test_risk_manager.py -v

# Run can_open_new_trade tests
pytest tests/unit/test_risk_manager.py -k can_open -v

# Run calculate_position tests
pytest tests/unit/test_risk_manager.py -k calculate_position -v
```

---

## Completion Checklist

- [ ] Read `core/risk_manager.py` and understood of structure
- [ ] Created `tests/unit/test_risk_manager.py` with proper imports
- [ ] Added required fixtures (mock_config, mock_logger)
- [ ] Created `test_can_open_new_trade` and all sub-tests pass
- [ ] Created `test_calculate_position` and all sub-tests pass
- [ ] All tests pass with `pytest tests/unit/test_risk_manager.py -v`
- [ ] NO source code files were modified

---

## Reference

- Source file: `core/risk_manager.py`
- Test file to create: `tests/unit/test_risk_manager.py`
