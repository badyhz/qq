# Codex Task: T205 Core Chain Regression Documentation

## Task ID
T205 - 核心链测试整理与回归入口规范（最小版）

## Overview
为已完成的 4 个核心模块测试创建回归文档和验证回归命令可用。

---

## Step-by-Step Instructions

### Step 1: Create Regression Documentation
Create `tests/REGRESSION.md` with following content:

```markdown
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
```

### Step 2: Verify Regression Commands
Run the core chain regression command to ensure it works:

```bash
./.venv/bin/python -m pytest tests/unit/ -v
```

Expected output should show:
- Tests collected from all 4 test files
- All tests pass
- No errors

---

## File Permissions

### Allowed to Modify/Create
- `tests/REGRESSION.md` - ONLY this file

### Forbidden to Modify (DO NOT TOUCH THESE FILES)
- All core/ source files (execution.py, risk_manager.py, order_manager.py, signal_engine.py, etc.)
- `main.py`
- `config.yaml`
- Any test files in `tests/unit/`
- `tests/conftest.py` - DO NOT create this
- Any other files in `tests/`

---

## Important Instructions

1. **ONLY CREATE REGRESSION DOCUMENT** - This is a documentation task only
2. **DO NOT CREATE conftest.py** - No shared fixtures
3. **DO NOT MODIFY EXISTING TESTS** - All test files stay as-is
4. **USE VENV PATH** - All commands must use `./.venv/bin/python`
5. **KEEP IT SIMPLE** - Just document existing tests, don't refactor

---

## Verification Commands

```bash
# Verify regression doc exists
cat tests/REGRESSION.md

# Run core chain regression
./.venv/bin/python -m pytest tests/unit/ -v

# Verify individual test files
./.venv/bin/python -m pytest tests/unit/test_execution.py -v
./.venv/bin/python -m pytest tests/unit/test_risk_manager.py -v
./.venv/bin/python -m pytest tests/unit/test_order_manager.py -v
./.venv/bin/python -m pytest tests/unit/test_signal_engine.py -v
```

---

## Completion Checklist

- [ ] Created `tests/REGRESSION.md` with proper content
- [ ] Regression doc lists all 4 test files
- [ ] Regression doc uses `./.venv/bin/python` paths
- [ ] Core chain regression command passes: `./.venv/bin/python -m pytest tests/unit/ -v`
- [ ] All 4 individual test files pass
- [ ] NO source code files were modified
- [ ] NO existing test files were modified
- [ ] NO conftest.py was created

---

## Reference

- Regression doc to create: `tests/REGRESSION.md`
- Test files (do NOT modify):
  - tests/unit/test_execution.py
  - tests/unit/test_risk_manager.py
  - tests/unit/test_order_manager.py
  - tests/unit/test_signal_engine.py
