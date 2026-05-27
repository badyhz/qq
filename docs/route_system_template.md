# Route System Template

## Overview

Reusable workflow patterns for systematic code integration projects. Extracted from execution_guard Phase2 (41 scripts, 9 batches, 0 regressions).

---

## Modes

### 1. Queue Mode

Sequential batch execution with state handoff.

```
batch N inject -> batch N test -> batch N docs sync -> batch N+1 inject
```

**When to use:**
- Code changes that affect shared state
- Sequential dependencies between batches
- Low-risk, high-volume integration

**Pattern:**
```
FOR each batch:
  1. AUDIT candidates (read-only)
  2. INJECT changes (code modification)
  3. TEST changes (targeted + regression)
  4. SYNC docs (update state)
  5. HANDOFF to next batch
```

**Rules:**
- Each step validates before next
- No step skips
- State is explicit between steps
- Rollback at batch boundary

### 2. DAG Mode

Parallel independent tasks with dependency gates.

```
T676 (inject) --o T681 (docs sync)
T677 (preflight) --o (informs T681)
T678 (milestone) --o (standalone)
T679 (batch8 audit) --o T682 (batch8 inject)
T680 (tracker) --o (standalone)
```

**When to use:**
- Independent analysis tasks
- Documentation updates (different files)
- Planning + execution can overlap
- Read-only audits

**Pattern:**
```
LAUNCH independent tasks in parallel:
  - audits (read-only)
  - projections (computation)
  - planning (analysis)

WAIT for dependencies:
  - code changes before doc sync
  - audits before injection

CONVERGE at batch boundaries
```

**Rules:**
- Independent reads -> parallel safe
- Independent writes -> parallel safe (different files)
- Dependent writes -> sequential
- Same-file writes -> sequential

### 3. Autopilot Mode

State-driven continuation without user prompts.

**When to use:**
- Repeatable patterns (same guard contract, same test pattern)
- Clear completion criteria
- Low decision complexity

**Pattern:**
```
WHILE not done:
  READ current state
  IDENTIFY next task
  EXECUTE task
  UPDATE state
  CHECK completion criteria
```

**Rules:**
- State is always read fresh (not assumed)
- Completion criteria are explicit
- Each iteration is self-contained
- User can interrupt at any point

### 4. Governance Mode

Policy enforcement at every layer.

**When to use:**
- Safety-critical systems
- Multi-phase projects
- Shared codebases
- Audit requirements

**Pattern:**
```
DEFINE policy (guard contract, kill-switches, frozen boundary)
ENFORCE at entry (CLI guard, test assertion)
VERIFY at exit (regression, docs sync)
AUDIT periodically (integrity check, coverage report)
```

**Rules:**
- Policy never drifts
- Enforcement is automatic
- Verification is explicit
- Audit is periodic

### 5. Closeout Mode

Standardized phase/milestone closure with git integrity verification.

**When to use:**
- Phase completion
- Milestone tag creation
- Release closure
- Any state that needs git-level integrity

**Pattern:**
```
PRE_CLOSEOUT → SCOPED_CLASSIFY → FROZEN_EXCLUSION → SCOPED_STAGE → COMMIT → TAG → VERIFY
```

**Stages:**

| Stage | Action | Gate |
|-------|--------|------|
| PRE_CLOSEOUT | Verify repo, HEAD, tags | All checks pass |
| SCOPED_CLASSIFY | Categorize dirty tree | Know what to stage/exclude |
| FROZEN_EXCLUSION | Check no frozen files staged | Empty frozen list |
| SCOPED_STAGE | Explicit file staging | No `git add .` |
| COMMIT | Descriptive closure commit | Clean message with metrics |
| TAG | Delete + recreate tag | Tag points to HEAD |
| VERIFY | Integrity checks | All pass |

**Rules:**
- NEVER use `git add .` or `git add -A`
- ALWAYS verify no frozen files staged
- ALWAYS delete + recreate tag (not force move)
- ALWAYS verify tag points to HEAD after tagging
- Classify dirty tree BEFORE staging

**Example:**
```bash
# PRE_CLOSEOUT
git rev-parse --is-inside-work-tree
git log --oneline -1
git tag -l 'phase2*'

# SCOPED_CLASSIFY
git status --short

# FROZEN_EXCLUSION
git diff --cached --name-only | grep -E "$FROZEN_PATTERNS"

# SCOPED_STAGE
git add scripts/{files}.py tests/unit/test_{files}_guard.py docs/{files}.md

# COMMIT
git commit -m "feat: complete {phase} ({count}/{total}, {coverage}%)"

# TAG
git tag -d {phase}-complete 2>/dev/null
git tag {phase}-complete

# VERIFY
git show {phase}-complete --quiet --format="%H"
git rev-parse HEAD  # must match
git status --short  # only frozen/junk remaining
```

**Failure modes:**
| Failure | Fix |
|---------|-----|
| Tag exists | Delete + recreate |
| Frozen staged | Unstage |
| Dirty after closeout | Add missing files |
| Tag wrong target | Delete + recreate |

**Closeout verification command:**
```bash
QQ_RUNTIME_MODE=dry_run python scripts/verify_engineering_closeout_state.py --tag {phase}-complete
```

---

## Hybrid Approach

Use the right mode for each task type:

| Task Type | Mode | Reason |
|-----------|------|--------|
| Code injection | Queue | Sequential, state-changing |
| Doc sync | DAG | Independent writes |
| Analysis/planning | DAG | Read-only, parallel |
| Testing | Queue | Sequential validation |
| Governance | Governance | Policy enforcement |
| Repetitive tasks | Autopilot | State-driven |
| Phase/milestone close | Closeout | Git-integrity closure |

---

## Workflow Protocol

### Task Definition

```markdown
## T{NNN} -- {Title}

Use {mode} mode.

Task: {description}

Allowed: {scope}
Modify only: {targets}
Guard contract: {policy}

Validation: {checks}
Output: {format}
```

### State Management

```markdown
## State

| Metric | Value |
|--------|-------|
| {key} | {value} |

## Batch Status

| Batch | Scripts | Status |
|-------|---------|--------|
| {N} | {count} | {DONE/PLANNED} |
```

### Completion Criteria

```markdown
## Done When

- [ ] {criterion 1}
- [ ] {criterion 2}
- [ ] {criterion 3}
```

### Parallel Launch

```markdown
## Launch

| Task | Agent | Status |
|------|-------|--------|
| T{N} | {description} | Running |
| T{N+1} | {description} | Running |
```

### Status Update

```markdown
## Status

| Task | Status |
|------|--------|
| T{N} | **PASS** |
| T{N+1} | Running |
```

---

## Prompt Compression Rules

1. **Terse task definitions**: Reduce token usage
2. **Structured output**: FILES/TESTS/RESULT/NOTES format
3. **Policy headers**: Prevent drift without verbosity
4. **Pattern references**: Avoid repeating known patterns
5. **State snapshots**: Capture current state, not assumed state

---

## Test Pattern Template

```python
from __future__ import annotations
import importlib
import sys
import pytest
from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = ["{script_name}"]

def test_import_safe():
    mod = importlib.import_module("scripts.{script_name}")
    assert hasattr(mod, "main")

def test_no_high_risk_imports():
    source = open("scripts/{script_name}.py", encoding="utf-8").read()
    for forbidden in ["binance_connector", "binance_http", "binance_testnet",
                       "broker_connector", "live_runner"]:
        assert forbidden not in source

def test_default_dry_run_allowed(monkeypatch):
    monkeypatch.delenv("QQ_RUNTIME_MODE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.{script_name} import main
    with pytest.raises(ValueError):
        main()

def test_dry_run_mode_allowed(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.{script_name} import main
    main()

def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.{script_name} import main
    with pytest.raises(ExecutionGuardError, match="live"):
        main()

def test_unknown_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "bogus")
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.{script_name} import main
    with pytest.raises(ValueError):
        main()
```

---

## Governance Board Template

```markdown
# {Project} Governance Board

## Phase Status

| Phase | Scope | Status | Scripts |
|-------|-------|--------|---------|
| Phase0 | {description} | {status} | {count} |
| Phase1 | {description} | {status} | {count} |
| Phase2 | {description} | {status} | {count} |

## Kill-Switch Coverage

| Kill Switch | Helper | Schema | Status Report | Contract |
|-------------|--------|--------|---------------|----------|
| {switch} | {helper} | {status} | {status} | {status} |

## Test Health

| Suite | Count | Status |
|-------|-------|--------|
| {suite} | {count} | {status} |

## Frozen Integrity

| Check | Result |
|-------|--------|
| {check} | {result} |
```

---

## Rollback Template

```markdown
## Rollback

To revert to pre-{phase} state:
\```bash
git checkout {tag}
\```

This restores the codebase to the point before {phase} changes.
```

---

## Metrics Tracking Template

```markdown
## Metrics

| Metric | Start | End | Delta |
|--------|-------|-----|-------|
| {metric} | {start} | {end} | {delta} |
```

---

## Key Learnings

1. **Batch size**: 5 scripts per batch balances speed and risk
2. **Parallel limit**: 5 independent agents max for context management
3. **Doc sync**: Build into batch completion, not separate task
4. **State reading**: Always read fresh state, never assume
5. **Policy retention**: Explicit policy headers prevent drift
6. **Test reuse**: Identical test patterns reduce cognitive load
7. **Governance boards**: Executive summary for stakeholders
8. **Retrospectives**: Capture lessons at phase boundaries
