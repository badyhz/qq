# Codex Task: T201 Execution Engine Unit Tests

## Task ID
T201 - execution.py 单元测试（最小版）

## Overview
为 `core/execution.py` 添加单元测试，只覆盖 dry-run 模式的核心逻辑和边界条件。

---

## Step-by-Step Instructions

### Step 1: Read Source Code
First, read `core/execution.py` to understand:
- The `ExecutionEngine.__init__` constructor signature
- What config keys are used (look for `config.get(...)` calls)
- What the `open_short` method returns in dry-run mode
- What fields are in the return dictionary

### Step 2: Create Test File
Create `tests/unit/` directory if it doesn't exist.
Create `tests/unit/test_execution.py` with the following structure:

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from core.execution import ExecutionEngine

# Fixtures will be added below

# Tests will be added below
```

### Step 3: Add Fixtures
Based on what you learned from reading `core/execution.py` in Step 1, create these fixtures:

1. `mock_config()` - Return a config dict with:
   - `mode`: "dry-run"
   - `execution` section with keys used by ExecutionEngine (dry_run_fee_rate, slippage_threshold, allow_live_without_protection)
   - Any other keys the constructor uses (e.g., "strategy_profile")

2. `mock_logger()` - Return a MagicMock object

3. `mock_order_manager()` - Return a MagicMock object

4. `mock_exchange()` - Return a MagicMock object

### Step 4: Test Dry-Run Success
Create test `test_dry_run_open_short_success`:

1. Use the fixtures from Step 3
2. Create a valid `position_plan`, `signal`, and `market` dict
3. Instantiate ExecutionEngine with the mocked dependencies
4. Call `engine.open_short(position_plan, signal, market)`
5. Assert the result matches what `core/execution.py` returns in dry-run mode:
   - `result["accepted"]` should be True
   - `result["mode"]` should be "dry-run"
   - Assert all key fields are present and correct based on source code

### Step 5: Test Invalid Quantity
Create test `test_open_short_invalid_quantity_rejected`:

1. Test with `quantity = 0.0` - should return accepted=False, reason="invalid_quantity"
2. Test with `quantity = -0.5` - should return accepted=False, reason="invalid_quantity"
3. Verify warning is logged

### Step 6: Verify Tests Run
Run: `pytest tests/unit/test_execution.py -v`

---

## File Permissions

### Allowed to Modify/Create
- `tests/unit/test_execution.py` - ONLY this file

### Forbidden to Modify (DO NOT TOUCH THESE FILES)
- `core/execution.py`
- `main.py`
- `config.yaml`
- `core/risk_manager.py`
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

1. **READ THE SOURCE FIRST** - Before writing any tests, read `core/execution.py` carefully
2. **ADAPT TO SOURCE CODE** - Don't use hardcoded values. Use what the actual code expects.
3. **USE MAGICK MIGG** - Mock all dependencies (config, logger, order_manager, exchange)
4. **ONLY TEST DRY-RUN** - Do not test live mode or ensure_live_protection
5. **KEEP IT SIMPLE** - Only test the specified scenarios

---

## Verification Commands

```bash
# Collect tests
pytest tests/unit/test_execution.py --collect-only

# Run all tests
pytest tests/unit/test_execution.py -v

# Run specific test
pytest tests/unit/test_execution.py::test_dry_run_open_short_success -v
```

---

## Completion Checklist

- [ ] Read `core/execution.py` and understood the structure
- [ ] Created `tests/unit/test_execution.py` with proper imports
- [ ] Added all required fixtures (mock_config, mock_logger, mock_order_manager, mock_exchange)
- [ ] Created `test_dry_run_open_short_success` and it passes
- [ ] Created `test_open_short_invalid_quantity_rejected` and it passes
- [ ] All tests pass with `pytest tests/unit/test_execution.py -v`
- [ ] NO source code files were modified

---

## Reference

- Source file: `core/execution.py`
- Test file to create: `tests/unit/test_execution.py`
