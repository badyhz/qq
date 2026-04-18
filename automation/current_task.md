# Codex Task: T203 Order Manager Unit Tests

## Task ID
T203 - order_manager.py 单元测试（最小版）

## Overview
为 `core/order_manager.py` 添加单元测试，只覆盖状态管理和平仓逻辑。

---

## Step-by-Step Instructions

### Step 1: Read Source Code
First, read `core/order_manager.py` to understand:
- The `OrderManager.__init__` constructor signature
- What config keys are used (look for `config.get(...)` calls)
- What `has_position()` and `can_open()` methods return
- What `open_position()` method creates and stores
- What `update_market()` method does in dry-run mode
- What `_close_position()` method returns (the closed trade dict)

### Step 2: Create Test File
Create `tests/unit/test_order_manager.py` with following structure:

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from core.order_manager import OrderManager

# Fixtures will be added below

# Tests will be added below
```

### Step 3: Add Fixtures
Based on what you learned from reading `core/order_manager.py` in Step 1, create these fixtures:

1. `mock_config()` - Return a config dict with:
   - `mode`: "dry-run"
   - Any other keys constructor uses (e.g., "strategy_profile")

2. `mock_execution_result()` - Return a valid execution result dict with:
   - accepted: True
   - mode: "dry-run"
   - All required fields that `open_position` expects

3. `mock_signal()` - Return a valid signal dict

4. `mock_market()` - Return a valid market dict with close, high, low, timestamp

### Step 4: Test State Flow (has_position, can_open, open_position)
Create tests for state transitions:

1. Test `has_position()` returns False initially
2. Test `can_open()` returns True initially
3. Test after `open_position()`:
   - `has_position()` returns True
   - `can_open()` returns False
   - Position has correct fields (entry_price, stop_price, take_profit_price, quantity, etc.)

For each test:
- Instantiate OrderManager with mock config
- Call methods and assert expected state changes
- Assert position dict has required keys from source code

### Step 5: Test Stop Loss / Take Profit Triggers
Create test `test_update_market_triggers_close`:

1. Create a position with mock data
2. Test stop loss trigger:
   - Create market with high >= stop_price
   - Call `update_market(market)`
   - Assert returns closed trade dict
   - Assert exit_reason is "STOP_LOSS"
3. Test take profit trigger:
   - Create position with mock data
   - Create market with low <= take_profit_price
   - Call `update_market(market)`
   - Assert returns closed trade dict
   - Assert exit_reason is "TAKE_PROFIT"
4. Test no trigger:
   - Create position
   - Create market within stop/tp range
   - Call `update_market(market)`
   - Assert returns None (no close)

For each test:
- Assert closed trade has expected fields based on `_close_position` source
- Verify pnl calculations if applicable

### Step 6: Verify Tests Run
Run: `pytest tests/unit/test_order_manager.py -v`

---

## File Permissions

### Allowed to Modify/Create
- `tests/unit/test_order_manager.py` - ONLY this file

### Forbidden to Modify (DO NOT TOUCH THESE FILES)
- `core/order_manager.py`
- `main.py`
- `config.yaml`
- `core/execution.py`
- `core/risk_manager.py`
- `core/signal_engine.py`
- `core/data_feed.py`
- `core/ticker_scanner.py`
- `core/trade_logger.py`
- `core/exchange.py`
- `utils/indicators.py`
- Any other files in `tests/` directory

---

## Important Instructions

1. **READ THE SOURCE FIRST** - Before writing any tests, read `core/order_manager.py` carefully
2. **ADAPT TO SOURCE CODE** - Don't use hardcoded values. Use what actual code expects.
3. **USE FIXTURES** - Create mock fixtures for test data
4. **ONLY TEST SPECIFIED METHODS** - Do not test `_update_excursions` or MAE/MFE
5. **KEEP IT SIMPLE** - Only test specified scenarios
6. **FOCUS ON DRY-RUN** - `update_market` only closes positions in dry-run mode

---

## Verification Commands

```bash
# Collect tests
pytest tests/unit/test_order_manager.py --collect-only

# Run all tests
pytest tests/unit/test_order_manager.py -v

# Run state flow tests
pytest tests/unit/test_order_manager.py -k "test_has_position or test_can_open or test_open_position" -v

# Run close trigger tests
pytest tests/unit/test_order_manager.py -k "test_update_market" -v
```

---

## Completion Checklist

- [ ] Read `core/order_manager.py` and understood structure
- [ ] Created `tests/unit/test_order_manager.py` with proper imports
- [ ] Added required fixtures (mock_config, mock_execution_result, mock_signal, mock_market)
- [ ] Created state flow tests and they pass
- [ ] Created stop loss / take profit trigger tests and they pass
- [ ] All tests pass with `pytest tests/unit/test_order_manager.py -v`
- [ ] NO source code files were modified

---

## Reference

- Source file: `core/order_manager.py`
- Test file to create: `tests/unit/test_order_manager.py`
