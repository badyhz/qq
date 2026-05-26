# Runtime Gate Design — HIGH_RISK_RUNTIME Only

## Scope

Applies only to HIGH_RISK_RUNTIME files:
- `core/live_runner.py`
- `scripts/live_playbook.py`
- `scripts/run_controlled_testnet_shift.py`
- `scripts/run_daily_shadow_scan_pipeline.py`
- `scripts/run_remediation_shadow_only_loop.py`
- `scripts/run_shadow_observation_experiments.py`
- `scripts/verify_risk_release_flow.py`

Not applicable to HIGH_RISK_WRITE or Phase 1-2 targets.

---

## 1. Default Dry-Run Runtime Policy

```
QQ_RUNTIME_MODE=dry_run
QQ_REQUIRE_DRY_RUN=1
```

- All runtime orchestrators default to dry-run
- Exchange calls mocked or skipped
- No live/testnet order submission without explicit unlock
- Layered unlock (layers 0-5) enforced per action
- Guard report emitted at startup showing all layers
- fail-closed: unknown mode halts runtime

---

## 2. No-Live Default

```
QQ_NO_LIVE=1  (always set unless explicitly overridden)
```

- Live mode requires all 5 layers + manual override
- Runtime gate blocks live mode by default
- Attempting live mode without full unlock raises `ExecutionGuardError`
- Log warning: "live mode attempted without full unlock"

---

## 3. Subprocess Child-Env Inheritance

- Parent process exports `QQ_NO_*` env vars before spawning children
- Child processes inherit kill-switch env vars automatically
- Explicit env passing required for `QQ_UNLOCK_*` vars
- No env leakage: parent unsets provider keys before spawning

```python
# Required pattern in all runtime orchestrators:
import os
child_env = os.environ.copy()
child_env["QQ_NO_SUBMIT"] = "1"
child_env["QQ_NO_CANCEL"] = "1"
child_env["QQ_NO_FLATTEN"] = "1"
child_env["QQ_NO_LIVE"] = "1"
subprocess.run([...], env=child_env)
```

---

## 4. Public-Fetch Only Mode

```
QQ_PUBLIC_FETCH_ONLY=1
```

- Allowed: readonly public market data fetches
- Allowed: report generation
- Allowed: dry-run planning
- Blocked: any exchange write operation
- Blocked: any order submission
- Blocked: any account modification

---

## 5. Local File Writer Boundaries

- Runtime scripts may write to `logs/` and `output/` directories only
- No writes to `core/`, `scripts/`, or config directories
- No writes to `~/.secrets/`, `~/.ai-routes/`, or env files
- File writes logged with path + size in guard report

---

## 6. Runtime Preflight Checklist

Before any runtime orchestrator executes (fail-closed):

1. [ ] `QQ_RUNTIME_MODE` is set and known
2. [ ] `QQ_REQUIRE_DRY_RUN` checked
3. [ ] Mode is not live (unless full layered unlock)
4. [ ] `QQ_NO_*` kill-switches checked
5. [ ] Symbol allowlist parsed
6. [ ] Guard report built and logged
7. [ ] Subprocess env prepared with QQ_NO_* inherited
8. [ ] Public-fetch-only flag respected
9. [ ] File writer boundaries checked

---

## 7. Runtime Guard Report Shape

```json
{
  "runtime_mode": "dry_run",
  "timestamp": "2026-05-26T...",
  "layers": {
    "layer0_kill_switch": {"QQ_NO_SUBMIT": false, "QQ_NO_CANCEL": false, "QQ_NO_FLATTEN": false, "QQ_NO_LIVE": true},
    "layer1_capability": true,
    "layer2_cli_allow": true,
    "layer3_env_unlock": false,
    "layer4_manual_confirm": false,
    "layer5_symbol_allowlist": ["BTCUSDT", "ETHUSDT"]
  },
  "public_fetch_only": true,
  "file_writes_allowed": ["logs/", "output/"],
  "blocked_actions": ["submit", "cancel", "flatten"]
}
```

---

## 8. Blocked Examples

### Missing mode
```
QQ_RUNTIME_MODE not set
=> ValueError: unknown execution mode: None
=> runtime halts, no exchange calls
```

### Live mode without unlock
```
QQ_RUNTIME_MODE=live
QQ_NO_LIVE not set
=> ExecutionGuardError: live mode not allowed
=> runtime halts
```

### Child process without inherited QQ_NO_*
```
Parent spawns child without QQ_NO_SUBMIT=1
=> child could potentially submit orders
=> REQUIRE: all runtime orchestrators export QQ_NO_* to child env
```

### Runtime wrapper calling submit path
```
live_playbook.py calls assert_submit_unlocked
=> layer3 env unlock not set
=> ExecutionGuardError: QQ_UNLOCK_SUBMIT not set for submit
=> submit path blocked
```

---

## 9. Allowed Examples

### Readonly public fetch
```
QQ_RUNTIME_MODE=dry_run
QQ_PUBLIC_FETCH_ONLY=1
=> fetch public ticker data
=> allowed, logged, no guard error
```

### Report generation
```
QQ_RUNTIME_MODE=dry_run
=> generate guard report
=> allowed, no exchange calls
```

### Dry-run planning
```
QQ_RUNTIME_MODE=dry_run
=> build signal plan
=> no submission, no exchange write
=> allowed
```
