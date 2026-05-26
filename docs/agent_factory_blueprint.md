# AI PMO / Agent Factory Blueprint

**Source**: Phase2 retrospective (41 scripts, 9 batches, 0 regressions)
**Purpose**: Formalize multi-agent orchestration as reusable agent factory architecture

---

## Architecture

```
Human PM
    |
Governance Board
    |
+-----------------------------------------+
|  AI Architect   |  AI Validator         |
|  AI Auditor     |  AI Docs Team        |
|  AI Code Team   |                       |
+-----------------------------------------+
    |
Execution Workers (parallel)
```

**Flow**: Human PM sets goals. Governance Board enforces policy. AI teams execute in parallel. Execution Workers handle individual tasks.

---

## Roles

### Human PM
- Defines goals and constraints
- Approves policy changes
- Handles escalations
- Makes unfreeze decisions (Phase3/Phase4 gates)
- Final arbiter on architectural conflicts

### Governance Board
- Source of truth for project state
- Tracks metrics, coverage, frozen integrity
- Generates reports (coverage dashboard, progress board)
- Enforces policy at every layer
- Maintains kill-switch coverage matrix

### AI Architect
- Designs implementation approach
- Defines task dependencies
- Plans batch sequences
- Reviews architectural decisions
- Determines Queue vs DAG mode per task

### AI Validator
- Runs test suites (targeted + regression)
- Verifies guard contracts
- Checks regression baseline (124 tests)
- Validates coverage metrics
- Reports PASS/FAIL per batch

### AI Auditor
- Checks frozen boundary (22 files)
- Verifies file integrity (no frozen modifications)
- Audits docs consistency
- Reviews git state before closeout
- Runs periodic integrity checks

### AI Docs Team
- Syncs documentation (8-10 files/wave)
- Updates metrics in governance board
- Maintains integration matrix
- Creates phase snapshots
- Keeps coverage dashboard current

### AI Code Team
- Injects code changes (5 scripts/batch)
- Creates test files (6-test pattern per script)
- Implements guard contracts
- Handles code review
- Reports FILES/TESTS/RESULT/NOTES per task

### Execution Workers
- Execute individual tasks
- Run in parallel when independent
- Report completion status
- Handle retries from last checkpoint
- Scoped to single task boundaries

---

## Task Routing

| Task Type | Route To | Mode |
|-----------|----------|------|
| Code injection | AI Code Team | Queue |
| Test creation | AI Code Team | Queue |
| Doc sync | AI Docs Team | DAG |
| Analysis | AI Architect | DAG |
| Validation | AI Validator | Queue |
| Audit | AI Auditor | DAG |
| Planning | AI Architect | DAG |
| Closeout | All teams | Sequential |
| Metrics update | Governance Board | DAG |
| Escalation | Human PM | On-demand |

### Mode Selection Rules
- **Queue**: Code changes that affect shared state, sequential dependencies
- **DAG**: Independent reads, independent writes to different files, analysis
- **Governance**: Policy enforcement at entry/exit/audit layers
- **Closeout**: Phase/milestone closure with git integrity
- **Autopilot**: Repeatable patterns with clear completion criteria

---

## Queue Ownership

| Queue | Owner | Capacity | Batch Size |
|-------|-------|----------|------------|
| Code injection | AI Code Team | 5 scripts/batch | 30 test points |
| Test creation | AI Code Team | 5 tests/batch | 6 tests per script |
| Doc sync | AI Docs Team | 8-10 files/wave | per batch completion |
| Validation | AI Validator | 1 batch at a time | regression baseline included |
| Audit | AI Auditor | 3-5 checks/wave | frozen boundary + integrity |
| Planning | AI Architect | 1 plan at a time | batch sequence definition |

---

## Parallel Execution Policy

### Safe Parallelism Rules
| Access Pattern | Parallel Safe? | Limit |
|---------------|----------------|-------|
| Independent reads | Yes | Unlimited |
| Independent writes (different files) | Yes | Up to 5 agents |
| Dependent writes | No | Sequential |
| Same-file writes | No | Sequential |

### Agent Limits

**5-agent mode** (standard):
```
Agent 1: Code injection (batch N)
Agent 2: Test creation (batch N)
Agent 3: Doc sync (batch N-1)
Agent 4: Validation (batch N-1)
Agent 5: Audit (batch N-2)
```

**10-agent mode** (complex waves):
```
Agent 1-2: Code injection (parallel batches)
Agent 3-4: Test creation (parallel)
Agent 5-6: Doc sync (parallel files)
Agent 7: Validation
Agent 8: Audit
Agent 9: Planning
Agent 10: Tracker
```

**Autopilot mode** (state-driven):
```
LOOP:
  READ state (fresh, never assumed)
  IDENTIFY next task
  EXECUTE task
  UPDATE state
  CHECK completion criteria
  IF done: BREAK
  ELSE: CONTINUE
```

### Dependency Handling
```
Task A --> Task B  (B waits for A)
Task C --> Task D  (D waits for C)
Task A, C parallel (independent)
Task B, D parallel (independent after A, C complete)
```

---

## Acceptance Gates

| Gate | Criteria | Enforced By |
|------|----------|-------------|
| Batch complete | Tests pass, docs synced, no regressions | AI Validator |
| Wave complete | All tasks PASS, frozen untouched | AI Auditor |
| Phase complete | Coverage 100%, regression baseline clean, metrics correct | Governance Board |
| Closeout | Tag points to HEAD, tree clean, frozen verified | AI Auditor |

### Gate Sequence
```
Batch Gate --> Wave Gate --> Phase Gate --> Closeout Gate
    |              |              |              |
  Validator      Auditor      Governance     Auditor
```

---

## Closeout Protocol

```
1. PRE_CLOSEOUT    - Verify repo, HEAD, existing tags
2. SCOPED_CLASSIFY - Categorize dirty tree (staged/unstaged/untracked)
3. FROZEN_EXCLUSION - Verify no frozen files in staging
4. SCOPED_STAGE    - Explicit file staging (NEVER git add .)
5. COMMIT          - Descriptive message with metrics
6. TAG             - Delete old tag + recreate at HEAD
7. VERIFY          - Tag matches HEAD, tree clean except frozen
```

### Closeout Rules
- NEVER use `git add .` or `git add -A`
- ALWAYS verify no frozen files staged before commit
- ALWAYS delete + recreate tag (not force move)
- ALWAYS verify tag points to HEAD after tagging
- Classify dirty tree BEFORE staging

### Closeout Verification
```bash
git show {tag} --quiet --format="%H"
git rev-parse HEAD  # must match
git status --short  # only frozen/junk remaining
```

---

## Failure Recovery

| Failure | Recovery | Owner |
|---------|----------|-------|
| Test failure | Fix, re-test, continue | AI Code Team |
| Frozen file staged | Unstage, investigate, re-verify | AI Auditor |
| Doc drift | Sync wave (next batch includes docs) | AI Docs Team |
| Tag conflict | Delete + recreate | AI Auditor |
| Agent crash | Restart from last checkpoint | Execution Worker |
| Coverage gap | Identify missing scripts, re-audit | AI Validator |
| Policy violation | Escalate to Human PM | Governance Board |

---

## Escalation Rules

| Condition | Escalate To | Severity |
|-----------|-------------|----------|
| Policy violation | Human PM | CRITICAL |
| Frozen boundary breach | Human PM | CRITICAL |
| Test regression (baseline) | Human PM | HIGH |
| Architectural conflict | AI Architect | HIGH |
| Resource conflict (same-file) | Human PM | MEDIUM |
| Doc drift beyond tolerance | AI Docs Team | MEDIUM |
| Batch velocity anomaly | AI Architect | LOW |

---

## Metrics Tracking

| Metric | Updated By | Frequency | Source |
|--------|------------|-----------|--------|
| TRUE_GUARDED | AI Code Team | Per batch | grep-verified |
| Coverage % | AI Validator | Per batch | TRUE_GUARDED / eligible |
| Test count | AI Validator | Per batch | pytest output |
| Frozen integrity | AI Auditor | Per wave | git diff check |
| Docs sync status | AI Docs Team | Per wave | file hash comparison |
| Regression baseline | AI Validator | Per batch | 124-test suite |
| Batch count | Governance Board | Per phase | task tracker |

---

## Communication Protocol

### Status Updates
```markdown
## Status

| Task | Status |
|------|--------|
| T{N} | **PASS** |
| T{N+1} | Running |
```

### Completion Reports
```markdown
## Completion

- Scripts: {count}
- Tests: {count}
- Regressions: 0
- Frozen: untouched
- Coverage: {pct}%
```

### Escalation Messages
```markdown
## Escalation

- Issue: {description}
- Severity: {CRITICAL/HIGH/MEDIUM}
- Action needed: {decision}
```

### Batch Handoff
```markdown
## Batch {N} Complete

- Injected: {count} scripts
- Tests: {count} passing
- Docs: {count} synced
- Frozen: {count} untouched
- Ready for: batch {N+1}
```

---

## Prompt Compression Rules

1. **Terse task definitions**: Reduce token usage, keep technical accuracy
2. **Structured output**: FILES/TESTS/RESULT/NOTES format
3. **Policy headers**: Prevent drift without verbose instructions
4. **Pattern references**: Reference existing patterns instead of repeating
5. **State snapshots**: Capture current state, never assume

---

## Applicability

This blueprint applies to any multi-agent code integration project with:
- Safety-critical constraints (frozen boundaries, policy enforcement)
- Parallel execution needs (independent reads/writes)
- Phase-gated delivery (batch -> wave -> phase -> closeout)
- Audit requirements (integrity, coverage, regression)

**Proven at**: Phase2 execution guard integration (41 scripts, 9 batches, 0 regressions, 100% coverage)
