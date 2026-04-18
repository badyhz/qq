# Core Chain Regression

## Overview
This regression suite tests the 4 core modules that form the main trading execution chain:
1. Execution Execution Engine (execution.py)
2. Risk Manager (risk_manager.py)
3. Order Manager (order_manager.py)
4. Signal Engine (signal_engine.py)

## Test Files
- `tests/unit/test_execution.py` - T201 completed
- `tests/unit/test_risk_manager.py` - T202 completed
- `tests/unit/test_order_manager.py` - T203 completed
- `tests/unit/test_signal_engine.py` - T204 completed

## Regression Commands

### Run All Core Chain Tests
```bash
./.venv/bin/python -m pytest tests/unit/ -v
```

### Run Individual Module Tests
```bash
# Execution engine tests
./.venv/bin/python -m pytest tests/unit/test_execution.py -v

# Risk manager tests
./.venv/bin/python -m pytest tests/unit/test_risk_manager.py -v

# Order manager tests
./.venv/bin/python -m pytest tests/unit/test_order_manager.py -v

# Signal engine tests
./.venv/bin/python -m pytest tests/unit/test_signal_engine.py -v
```

### Run by Test Name Pattern
```bash
# Test specific functions
./.venv/bin/python -m pytest tests/unit/ -k "test_open_short" -v
./.venv/bin/python -m pytest tests/unit/ -k "test_can_open" -v
./.venv/bin/python -m pytest tests/unit/ -k "test_state" -v
./.venv/bin/python -m pytest tests/unit/ -k "test_on_candle" -v
```

## Completion Status
- [x] T201: execution.py unit tests
- [x] T202: risk_manager.py unit tests
- [x] T203: order_manager.py unit tests
- [x] T204: signal_engine.py unit tests

## Notes
- All tests use dry-run mode
- No live trading code is tested
- No external APIs are called
- Tests are designed to be fast and deterministic
