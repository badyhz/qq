# Workflow Pattern Library

## Overview

Reusable engineering patterns extracted from Execution Guard Phase2 (41 scripts, 9 batches, 0 regressions). Each pattern solves a specific problem class with proven parallelism and validation rules.

**Source:** Phase2 retrospective + route system template.

---

## Pattern 1: SAFE_READONLY_AUDIT

**Purpose:** Audit non-frozen scripts for guard eligibility.

**Inputs:**
- Candidate script list
- Frozen file list
- Guard contract definition

**Outputs:**
- Eligible/NOT_ELIGIBLE classification
- Risk assessment per script
- Batch recommendations

**Parallelism profile:** DAG (independent reads)

**Expected risks:**
- False positives (scripts that look safe but aren't)
- Missing frozen files in exclusion list
- Import analysis gaps

**Validation rules:**
- Script exists in `scripts/` directory
- Has `main()` function
- Not in frozen list
- No high-risk imports (`binance_connector`, `binance_http`, `binance_testnet`, `broker_connector`, `live_runner`)
- Not already guarded

**Anti-patterns:**
- Don't skip frozen exclusion check
- Don't assume scripts are safe without reading them
- Don't batch too many (keep to 5 per batch)

---

## Pattern 2: GUARD_INJECTION_BATCH

**Purpose:** Inject guard contract into 5 scripts per batch.

**Inputs:**
- 5 approved scripts from audit
- Guard contract definition (`normalize_execution_mode` + `assert_dry_run_required`)
- Test pattern template (6-test pattern)

**Outputs:**
- 5 guarded scripts
- 5 test files (6 tests each)
- Test results (30/30 pass)

**Parallelism profile:** Queue (sequential per batch)

**Expected risks:**
- Guard placement errors (not first 2 lines in `main()`)
- Missing imports (`os`, `core.execution_guards`)
- Test file naming mismatches
- Argparse conflicts in tests

**Validation rules:**
- Guard is first 2 lines in `main()`
- No high-risk imports
- 6/6 tests pass
- No regression in baseline

**Anti-patterns:**
- Don't inject guard inside argparse logic
- Don't skip regression testing
- Don't batch more than 5 scripts
- Don't forget to check for existing imports

---

## Pattern 3: DOCS_SYNC_WAVE

**Purpose:** Synchronize all docs to reflect current state.

**Inputs:**
- Current metrics (TRUE_GUARDED, coverage, tests)
- Stale doc list
- Expected values

**Outputs:**
- Updated docs (8-13 files)
- Staleness report
- Consistency verification

**Parallelism profile:** DAG (independent writes, different files)

**Expected risks:**
- Count drift (old numbers lingering)
- Missing inventory entries
- Inconsistent batch status
- Broken markdown tables

**Validation rules:**
- All stale counts updated
- All inventory lists complete
- All batch statuses correct
- All metrics consistent

**Anti-patterns:**
- Don't edit same doc from multiple agents
- Don't skip verification after sync
- Don't assume counts are correct without checking
- Don't forget to update Audit Snapshot sections

---

## Pattern 4: INTEGRITY_CLEANUP_WAVE

**Purpose:** Resolve inventory accounting drift and classification issues.

**Inputs:**
- Current guarded count
- Classification taxonomy
- Known anomalies (e.g., META_GUARD_TOOLING misclassification)

**Outputs:**
- Corrected counts
- Updated taxonomy
- Resolved anomalies
- Integrity report

**Parallelism profile:** DAG (independent analysis tasks)

**Expected risks:**
- META_GUARD_TOOLING misclassification
- Orphan test files
- Count mismatches between docs
- Stale classification rules

**Validation rules:**
- Grep-verified guarded count
- All scripts classified
- No orphan tests
- All docs consistent

**Anti-patterns:**
- Don't trust doc counts without grep verification
- Don't skip META_GUARD_TOOLING distinction
- Don't ignore orphan tests
- Don't leave classification ambiguous

---

## Pattern 5: PRECISION_LANDING

**Purpose:** Final batch execution with complete closure.

**Inputs:**
- Final script(s) to guard
- All docs preflighted
- Completion criteria defined

**Outputs:**
- Final guarded scripts
- Final test results
- Completion checkpoint
- Governance board updated

**Parallelism profile:** Queue (sequential, high precision)

**Expected risks:**
- Last-mile regressions
- Doc sync missed fields
- Tag target mismatch
- Frozen file accidental inclusion

**Validation rules:**
- All scripts guarded (41/41)
- All tests pass
- All docs synced
- Tag points to HEAD
- Working tree clean (except frozen)

**Anti-patterns:**
- Don't rush the final batch
- Don't skip verification steps
- Don't create tag before commit
- Don't forget to verify frozen boundary

---

## Pattern 6: ENGINEERING_CLOSEOUT

**Purpose:** Standardized phase/milestone closure with git integrity verification.

**Inputs:**
- Phase completion confirmed
- All work committed
- Tests passing

**Outputs:**
- Closure commit
- Closure tag
- Integrity verification
- Rollback documentation

**Parallelism profile:** Sequential (verify -> stage -> commit -> tag -> verify)

**Expected risks:**
- Dirty tree after closeout
- Tag points to wrong commit
- Frozen files accidentally committed
- Missing files in commit

**Validation rules:**
- Tag points to HEAD
- No frozen files staged
- All phase work committed
- Working tree only has frozen/junk
- Regression passes

**Anti-patterns:**
- Don't use `git add .` (use scoped staging)
- Don't tag before commit
- Don't skip frozen exclusion check
- Don't forget to verify tag target

---

## Pattern 7: PARALLEL_WAVE

**Purpose:** Execute multiple independent tasks simultaneously.

**Inputs:**
- Task list with dependencies
- Agent pool
- Parallelism rules

**Outputs:**
- All tasks complete
- No file conflicts
- Dependency gates respected

**Parallelism profile:** DAG (max 5 agents standard, 10 agents complex)

**Expected risks:**
- File collision between agents
- Dependency violation
- Context limit overflow
- Agent crash mid-task

**Validation rules:**
- No two agents edit same file
- Dependencies respected
- All tasks report status
- No regressions

**Anti-patterns:**
- Don't launch agents that edit same file
- Don't ignore dependency gates
- Don't exceed agent limits
- Don't skip status checks

---

## Pattern 8: STATE_DRIVEN_CONTINUATION

**Purpose:** Autonomous progress without user prompts.

**Inputs:**
- Current state
- Completion criteria
- Task queue

**Outputs:**
- Progress made
- State updated
- Completion check

**Parallelism profile:** Autopilot (sequential iterations)

**Expected risks:**
- Stale state reading
- Infinite loop
- Missed completion criteria
- Drift from original goals

**Validation rules:**
- State read fresh each iteration
- Completion criteria checked
- Progress made each cycle
- User can interrupt

**Anti-patterns:**
- Don't assume state without reading
- Don't skip completion check
- Don't continue after error
- Don't ignore user interrupts

---

## Anti-Pattern Summary

| Anti-Pattern | Pattern | Consequence |
|---|---|---|
| `git add .` | CLOSEOUT | Frozen files committed |
| Skip regression | INJECTION | Regressions shipped |
| Trust doc counts | INTEGRITY | Count drift |
| Edit same file in parallel | WAVE | File corruption |
| Tag before commit | CLOSEOUT | Tag points to wrong commit |
| Skip frozen check | AUDIT | Frozen files modified |
| Batch >5 scripts | INJECTION | Risk too high |
| Assume state | AUTOPILOT | Stale decisions |

---

## Mode Reference

Quick mapping from route system template:

| Task Type | Mode | Pattern |
|---|---|---|
| Code injection | Queue | GUARD_INJECTION_BATCH |
| Doc sync | DAG | DOCS_SYNC_WAVE |
| Analysis/planning | DAG | SAFE_READONLY_AUDIT |
| Testing | Queue | GUARD_INJECTION_BATCH |
| Governance | Governance | ENGINEERING_CLOSEOUT |
| Repetitive tasks | Autopilot | STATE_DRIVEN_CONTINUATION |
| Phase/milestone close | Closeout | ENGINEERING_CLOSEOUT |

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
