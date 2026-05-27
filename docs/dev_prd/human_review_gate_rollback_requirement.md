# Human Review Gate Rollback Requirement

## Overview

Every gate must have a documented rollback plan. If an approved action causes issues, the rollback must be executable without additional human decision-making.

## Rollback by Gate Type

### TRADING Gate Rollback

**Steps:**
1. Cancel all pending orders (dry-run or live)
2. Reset order_manager state to pre-action snapshot
3. Verify no orders in flight
4. Restore risk_manager to pre-action limits

**Verification command:**
```bash
python3 -c "from core.order_manager import OrderManager; om = OrderManager(); print(om.get_open_orders())"
```

**Expected outcome:** Empty open orders list. Risk limits at pre-action values.

### CREDENTIAL Gate Rollback

**Steps:**
1. Revoke any newly issued credentials
2. Restore credential storage to pre-action state
3. Verify no credential leaks in logs
4. Confirm env vars restored

**Verification command:**
```bash
python3 -c "from utils.config_loader import load_config; c = load_config(); print('config loaded, no secrets exposed')"
```

**Expected outcome:** Config loads cleanly. No secret values in output.

### CONNECTION Gate Rollback

**Steps:**
1. Close all active connections
2. Reset connection state to disconnected
3. Verify no pending requests
4. Confirm testnet endpoint used (not live)

**Verification command:**
```bash
python3 -c "from core.data_feed import DataFeed; df = DataFeed(); print(df.get_connection_state())"
```

**Expected outcome:** Connection state is 'disconnected'.

### PLANNER Gate Rollback

**Steps:**
1. Disconnect planner from execution pipeline
2. Clear planner output buffer
3. Reset signal_engine to independent mode
4. Verify no planner-driven orders pending

**Verification command:**
```bash
python3 -c "from core.signal_engine import SignalEngine; se = SignalEngine(); print(se.get_mode())"
```

**Expected outcome:** Signal engine mode is 'independent'.

### FROZEN_FILE Gate Rollback

**Steps:**
1. Restore frozen file from backup
2. Re-verify freeze tag integrity
3. Run affected module tests
4. Confirm no contamination of other frozen files

**Verification command:**
```bash
python3 -c "
import hashlib
with open('core/risk_manager.py','rb') as f:
    print('risk_manager hash:', hashlib.sha256(f.read()).hexdigest())
"
```

**Expected outcome:** Hash matches known-good value. Tests pass.

### RISK_PARAMETER Gate Rollback

**Steps:**
1. Restore risk parameters to pre-action values
2. Verify risk_manager loaded with correct limits
3. Confirm no risk bypass paths active
4. Run risk manager tests

**Verification command:**
```bash
python3 -c "from core.risk_manager import RiskManager; rm = RiskManager(); print(rm.get_limits())"
```

**Expected outcome:** Limits match pre-action values. All tests pass.

## General Rollback Rules

1. Rollback must be deterministic — same steps, same outcome.
2. Rollback must not require additional human decisions.
3. Rollback verification must produce a PASS/FAIL result.
4. Failed rollback triggers L4 escalation.
5. All rollback executions are logged in gate history.
