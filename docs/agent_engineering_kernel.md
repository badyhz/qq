# Agent Engineering Kernel

## Overview

Reusable workflow system extracted from Execution Guard Phase2 (41 scripts, 9 batches, 0 regressions). Defines operational modes for AI-driven engineering projects.

## Evolution

```
prompt-driven -> queue-driven -> state-driven -> governance-driven
```

| Stage | Description | Phase2 Example |
|-------|-------------|----------------|
| Prompt-driven | Human gives each command | Initial batch1-2 |
| Queue-driven | Sequential batch execution | Batch3-5 injection |
| State-driven | AI reads state, continues autonomously | Batch6-9 + docs sync |
| Governance-driven | Policy enforced at every layer | Full Phase2 lifecycle |

## Modes

### 1. POLICY_MODE

**Purpose:** Define non-negotiable constraints that never drift.

**When to use:**
- Safety-critical systems
- Multi-phase projects
- Any work with frozen boundaries

**Parallelism rules:** Policy is read once, enforced everywhere. No parallel policy changes.

**Stop conditions:**
- Policy violation detected
- Frozen boundary breached
- Kill-switch triggered

**Human responsibilities:**
- Define initial policy
- Approve policy changes
- Review unfreeze decisions

**AI responsibilities:**
- Enforce policy at every entry point
- Never modify policy without approval
- Report policy violations immediately

**Example:**
```
POLICY:
- Guard contract: assert_dry_run_required at CLI entry
- FAIL-CLOSED: no implicit fallback
- Frozen boundary: 22 files, zero modification
- Kill-switches: QQ_NO_SUBMIT, QQ_NO_CANCEL, QQ_NO_FLATTEN, QQ_NO_LIVE, QQ_REQUIRE_DRY_RUN
```

### 2. QUEUE_MODE

**Purpose:** Sequential batch execution with state handoff.

**When to use:**
- Code changes that affect shared state
- Sequential dependencies between batches
- Low-risk, high-volume integration

**Parallelism rules:** One batch at a time. Each step validates before next.

**Stop conditions:**
- Test failure
- Frozen file conflict
- Regression detected

**Human responsibilities:**
- Approve batch candidates
- Review test results
- Handle escalations

**AI responsibilities:**
- Execute inject -> test -> sync sequence
- Maintain state between batches
- Report completion per batch

**Example:**
```
FOR each batch:
  1. AUDIT candidates (read-only)
  2. INJECT changes (code modification)
  3. TEST changes (targeted + regression)
  4. SYNC docs (update state)
  5. HANDOFF to next batch
```

### 3. DAG_MODE

**Purpose:** Parallel independent tasks with dependency gates.

**When to use:**
- Independent analysis tasks
- Documentation updates (different files)
- Planning + execution overlap
- Read-only audits

**Parallelism rules:**
- Independent reads -> parallel safe
- Independent writes -> parallel safe (different files)
- Dependent writes -> sequential
- Same-file writes -> sequential

**Stop conditions:**
- Dependency conflict
- File collision
- Context limit reached

**Human responsibilities:**
- Define task dependencies
- Resolve conflicts
- Approve parallel launches

**AI responsibilities:**
- Respect dependency gates
- Avoid file collisions
- Report parallel completion status

**Example:**
```
T676 (inject) ---> T681 (docs sync)
T677 (preflight) ---> (informs T681)
T678 (milestone) ---> (standalone)
T679 (batch8 audit) ---> T682 (batch8 inject)
T680 (tracker) ---> (standalone)
```

### 4. AUTOPILOT_MODE

**Purpose:** State-driven continuation without user prompts.

**When to use:**
- Repeatable patterns (same guard contract, same test pattern)
- Clear completion criteria
- Low decision complexity

**Parallelism rules:** One iteration at a time. State read fresh each cycle.

**Stop conditions:**
- Completion criteria met
- Error encountered
- User interrupt

**Human responsibilities:**
- Define completion criteria
- Monitor progress
- Handle exceptions

**AI responsibilities:**
- Read current state
- Identify next task
- Execute and update state
- Check completion criteria

**Example:**
```
WHILE not done:
  READ current state
  IDENTIFY next task
  EXECUTE task
  UPDATE state
  CHECK completion criteria
```

### 5. GOVERNANCE_MODE

**Purpose:** Policy enforcement at every layer.

**When to use:**
- Safety-critical systems
- Multi-phase projects
- Shared codebases
- Audit requirements

**Parallelism rules:** Governance checks are sequential (cannot parallelize verification).

**Stop conditions:**
- Governance check fails
- Audit reveals drift
- Integrity violation

**Human responsibilities:**
- Define governance rules
- Review audit results
- Approve exceptions

**AI responsibilities:**
- Enforce governance at every step
- Generate audit reports
- Maintain integrity logs

**Example:**
```
DEFINE policy (guard contract, kill-switches, frozen boundary)
ENFORCE at entry (CLI guard, test assertion)
VERIFY at exit (regression, docs sync)
AUDIT periodically (integrity check, coverage report)
```

### 6. CLOSEOUT_MODE

**Purpose:** Standardized phase/milestone closure with git integrity.

**When to use:**
- Phase completion
- Milestone tag creation
- Release closure

**Parallelism rules:** Closeout is sequential (verify -> stage -> commit -> tag -> verify).

**Stop conditions:**
- Verification failure
- Frozen file detected in staging
- Tag conflict

**Human responsibilities:**
- Approve closure
- Create tag (or approve AI creation)
- Verify final state

**AI responsibilities:**
- Execute closeout pipeline
- Verify integrity
- Report closure status

**Example:**
```
PRE_CLOSEOUT -> SCOPED_CLASSIFY -> FROZEN_EXCLUSION -> SCOPED_STAGE -> COMMIT -> TAG -> VERIFY
```

## Hybrid Approach

| Task Type | Mode | Reason |
|-----------|------|--------|
| Code injection | Queue | Sequential, state-changing |
| Doc sync | DAG | Independent writes |
| Analysis/planning | DAG | Read-only, parallel |
| Testing | Queue | Sequential validation |
| Governance | Governance | Policy enforcement |
| Repetitive tasks | Autopilot | State-driven |
| Phase closure | Closeout | Git integrity |

## Policy Headers

Policy headers prevent drift without verbose instructions.

```
POLICY:
- Guard contract: {definition}
- FAIL-CLOSED: {rule}
- Frozen boundary: {files}
- Kill-switches: {list}
```

## Guardrails

| Guardrail | Purpose | Enforcement |
|-----------|---------|-------------|
| Frozen boundary | Prevent high-risk changes | Git diff check |
| Kill-switches | Runtime safety | Environment variables |
| Test gates | Quality assurance | pytest pass required |
| Doc sync | State consistency | Metrics match |
| Closeout verification | Git integrity | Tag + HEAD match |

## Checkpoint System

| Checkpoint | When | What |
|------------|------|------|
| Batch complete | After each batch | Tests pass, docs synced |
| Wave complete | After parallel wave | All tasks PASS |
| Phase complete | After all batches | Coverage 100%, regression clean |
| Closeout | After phase | Tag points to HEAD, tree clean |

## Verification Bundles

```
INTEGRITY_BUNDLE:
  git status --short
  git diff --stat
  pytest regression

TAG_BUNDLE:
  git tag | tail
  git show {tag}

ROLLBACK_BUNDLE:
  git checkout {tag} --dry-run

CLOSEOUT_BUNDLE:
  verify clean tree
  verify frozen exclusion
  verify tag target
  verify regression
```

## Task Definition Protocol

```markdown
## T{NNN} -- {Title}

```text
Use {mode} mode.

Task: {description}

Allowed: {scope}
Modify only: {targets}
Guard contract: {policy}

Validation: {checks}
Output: {format}
```
```

## State Management

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

## Completion Criteria

```markdown
## Done When

- [ ] {criterion 1}
- [ ] {criterion 2}
- [ ] {criterion 3}
```
