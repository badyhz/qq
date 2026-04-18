# Codex Task: T204 Signal Engine Unit Tests

## Task ID
T204 - signal_engine.py 单元测试（最小版）

## Overview
为 `core/signal_engine.py` 添加单元测试，只覆盖状态机基础流转和非信号路径。

---

## Step-by-Step Instructions

### Step 1: Read Source Code
First, read `core/signal_engine.py` to understand:
- The `SignalEngine.__init__` constructor signature
- What config keys are used (look for `config.get(...)` calls)
- What state machine states exist (IDLE, ARMED, TRIGGERED, IN_POSITION, COOLDOWN)
- What methods change state (on_position_opened, on_trade_closed, on_candle)
- What `on_candle` returns in different scenarios

### Step 2: Create Test File
Create `tests/unit/test_signal_engine.py` with following structure:

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from core.signal_engine import SignalEngine

# Fixtures will be added below

# Tests will be added below
```

### Step 3: Add Fixtures
Based on what you learned from reading `core/signal_engine.py` in Step 1, create these fixtures:

1. `mock_config()` - Return a config dict with:
   - `strategy` section with keys used by SignalEngine
   - Any other keys constructor uses

2. `mock_logger()` - Return a MagicMock object

3. `mock_candle()` - Return a valid candle dict with timestamp, close, high, low, volume

### Step 4: Test State Machine Flow
Create tests for state transitions:

1. Test initial state is IDLE
2. Test `on_position_opened()` changes state to IN_POSITION
3. Test `on_trade_closed()` with cooldown > 0 changes state to COOLDOWN
4. Test `on_trade_closed()` with cooldown = 0 changes state to IDLE
5. Test cooldown completion returns state to IDLE (call on_candle enough times)

For each test:
- Instantiate SignalEngine with mock config
- Call state-changing methods
- Assert state matches expected value
- Use whatever state checking method exists or access private state if needed

### Step 5: Test on_candle Non-Signal Paths
Create test `test_on_candle_returns_none_when_no_signal`:

1. Test when insufficient data (not enough candles) - returns action="NONE"
2. Test when already has position - returns action="NONE"
3. Test when in cooldown - returns action="NONE"
4. Test when conditions not met for signal - returns action="NONE"

For each test:
- Set up SignalEngine with appropriate state
- Create mock candle data
- Call `signal_engine.on_candle(candle, has_position=...)`
- Assert returned dict has `action` key
- Assert `action` is "NONE"
- Do NOT test actual SHORT signal triggers
- Do NOT make precise assertions on indicator values

### Step 6: Verify Tests Run
Run: `pytest tests/unit/test_signal_engine.py -v`

---

## File Permissions

### Allowed to Modify/Create
- `tests/unit/test_signal_engine.py` - ONLY this file

### Forbidden to Modify (DO NOT TOUCH THESE FILES)
- `core/signal_engine.py`
- `main.py`
- `config.yaml`
- `core/execution.py`
- `core/risk_manager.py`
- `core/order_manager.py`
- `core/data_feed.py`
- `core/ticker_scanner.py`
- `core/trade_logger.py`
- `core/exchange.py`
- `utils/indicators.py`
- Any other files in `tests/` directory

---

## Important Instructions

1. **READ THE SOURCE FIRST** - Before writing any tests, read `core/signal_engine.py` carefully
2. **ADAPT TO SOURCE CODE** - Don't use hardcoded values. Use what actual code expects.
3. **USE MAGICMOCK** - Mock logger dependency
4. **ONLY TEST NON-SIGNAL PATHS** - Do NOT test actual SHORT signal triggers
5. **DO NOT TEST ARMED STATE** - Focus on IDLE, IN_POSITION, COOLDOWN transitions
6. **NO PRE- INDICATOR ASSERTIONS** - Don't assert exact EMA/VWAP/ATR values
7. **KEEP IT SIMPLE** - Only test specified scenarios

---

## Verification Commands

```bash
# Collect tests
pytest tests/unit/test_signal_engine.py --collect-only

# Run all tests
pytest tests/unit/test_signal_engine.py -v

# Run state machine tests
pytest tests/unit/test_signal_engine.py -k "test_state" -v

# Run on_candle tests
pytest tests/unit/test_signal_engine.py -k "test_on_candle" -v
```

---

## Completion Checklist

- [ ] Read `core/signal_engine.py` and understood structure
- [ ] Created `tests/unit/test_signal_engine.py` with proper imports
- [ ] Added required fixtures (mock_config, mock_logger, mock_candle)
- [ ] Created state flow tests and they pass
- [ ] Created non-signal path tests and they pass
- [ ] All tests pass with `pytest tests/unit/test_signal_engine.py -v`
- [ ] NO source code files were modified

---

## Reference

- Source file: `core/signal_engine.py`
- Test file to create: `tests/unit/test_signal_engine.py`
