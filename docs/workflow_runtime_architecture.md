# Workflow Runtime Architecture

Snapshot: 2026-05-27 (T716)

## 1. Stack Overview

```
Layer 4 (CLI Entry)     scripts/workflow_cli.py, scripts/workflow_status.py
Layer 3 (Orchestration) core/workflow_runner.py, core/workflow_scheduler.py
Layer 2 (Governance)    core/governance_state.py, core/workflow_lock_manager.py,
                        core/component_ownership.py, core/merge_review.py
Layer 1 (Engine)        core/agent_factory.py, core/worker_pool.py,
                        core/workflow_loader.py, core/workflow_safety.py
```

Versions:
- v1 (agent_factory + worker_pool): task graph + slot tracker
- v2 (workflow_runner + workflow_loader): template-driven orchestration
- v3 (governance_state + lock/ownership/merge): multi-agent collision prevention
- v4 (real agent adapters): **deferred** -- no live execution, no trading

## 2. Data Flow

```
  YAML/Python templates
         |
  workflow_loader (validate + load)
         |
  workflow_runner (build task graph)
    |         |
    v         v
agent_factory  governance_state
  (waves)      (state machine)
    |         |
    v         v
worker_pool    workflow_lock_manager
  (slots)      (exclusive access)
                   |
            component_ownership
              (who owns what)
                   |
             merge_review
              (conflict detect + resolve)
                   |
  workflow_cli / workflow_status (render)
```

## 3. Component Descriptions

### Layer 1 -- Engine

| Component | File | Role |
|---|---|---|
| AgentFactory | `core/agent_factory.py` | Task graph with 3 modes: QUEUE (sequential), DAG (parallel waves), CLOSEOUT (7-step verification). Plans execution waves. |
| WorkerPool | `core/worker_pool.py` | Slot-based concurrency tracker. N workers, assign/release/status. Pure simulation -- no real threads. |
| WorkflowLoader | `core/workflow_loader.py` | Loads YAML or Python dict templates from `automation/workflow_templates/`. Validates required fields (name, mode, tasks, parallel_policy). |
| WorkflowSafetyValidator | `core/workflow_safety.py` | Policy gate. Blocks forbidden task patterns (live_runner, submit_order, etc.), forbidden modes (LIVE_EXECUTION, REAL_TRADING), frozen file access, invalid state transitions. |

### Layer 2 -- Governance

| Component | File | Role |
|---|---|---|
| GovernanceStateMachine | `core/governance_state.py` | Formal 8-state lifecycle: NEW -> READY -> RUNNING -> PASS/PARTIAL/FAIL -> CLOSED. Enforces valid transitions. Tracks history. Supports closeout verification. |
| WorkflowLockManager | `core/workflow_lock_manager.py` | Exclusive locks per component path. Reentrant for same task. Raises LockError on conflict. Supports force_release for admin. |
| ComponentOwnershipRegistry | `core/component_ownership.py` | Registers owner_task per component_path. exclusive or shared permission. ConflictError on cross-task writes. |
| MergeReviewPipeline | `core/merge_review.py` | Merge request lifecycle: proposed -> reviewing -> accepted/rejected. Auto-detects conflict when candidate hash != canonical. |

### Layer 3 -- Orchestration

| Component | File | Role |
|---|---|---|
| WorkflowRunner | `core/workflow_runner.py` | Connects agent_factory + governance_state + templates. Builds tasks from template, computes plan, simulates execution. |
| WorkflowScheduler | `core/workflow_scheduler.py` | Step-by-step scheduler. Resolves ready tasks, assigns to WorkerPool, transitions governance state, logs execution. |

### Layer 4 -- CLI Entry

| Component | File | Role |
|---|---|---|
| workflow_cli | `scripts/workflow_cli.py` | `--workflow NAME` or `--mode queue/dag/closeout`. Loads template, runs simulation, prints results. Requires QQ_RUNTIME_MODE=dry_run. |
| workflow_status | `scripts/workflow_status.py` | Renders demo workflow state: task list, dependency graph, worker allocation, progress bar. |

## 4. Safety Boundaries

Hard constraints enforced at multiple layers:

- **Simulation only**: Every core module docstring declares "Simulation only. No real agent execution."
- **No real agent execution**: AgentFactory plans waves but never invokes external agents.
- **No trading**: `workflow_safety.py` forbids task patterns: `submit_order`, `cancel_order`, `flatten_position`, `live_mode`, `live_runner`.
- **Frozen files**: 19 script patterns are frozen (live_runner, submit_approved, etc.) -- tasks accessing them trigger CRITICAL violation.
- **Execution guards**: CLI entry points call `assert_dry_run_required()` and `normalize_execution_mode()` from `core/execution_guards.py`.
- **Forbidden modes**: `LIVE_EXECUTION`, `REAL_TRADING`, `PLANNER_MODE` rejected at validation.

## 5. Governance Layer

Three mechanisms prevent multi-agent collisions:

### Ownership Registry
- Task registers exclusive claim on component_path before writing
- ConflictError if different task tries same path
- shared permission allows read-only concurrent access

### Lock Manager
- Acquire/release exclusive locks per component path
- Reentrant: same task can re-acquire
- force_release available for admin intervention

### Merge Review Pipeline
- Propose: candidate hash vs canonical hash
- Auto-conflict detection when hashes diverge
- Review -> Accept (updates canonical) or Reject
- Tracks all open MRs per component

## 6. Collision Prevention (T707 vs T710)

Scenario: Two tasks (T707, T710) both target `core/signal_engine.py`.

Without governance:
- Both tasks write simultaneously
- Last writer wins, first writer's changes lost
- No audit trail of who changed what

With governance:
1. T707 acquires ownership on `core/signal_engine.py` (ComponentOwnershipRegistry)
2. T710 attempts register -> ConflictError raised
3. T710 must wait or re-target
4. If T707 proposes merge, MergeReviewPipeline tracks candidate vs canonical
5. T710 can detect open MRs via `detect_conflicts()`
6. Accept/reject flow ensures only one change lands

Lock layer adds runtime exclusion: even if ownership is released, the lock prevents concurrent write during the actual operation window.

## 7. Future v4 Adapter Boundary

v4 will add real agent adapters (Claude Code, subagents, external tools). Current boundary:

```
v1-v3 (current)          v4 (deferred)
AgentFactory             RealAgentAdapter (abstract)
  plan waves               execute via API
  simulate only            actual tool calls
WorkerPool               ProcessPool / ThreadPool
  slot tracking            real concurrency
WorkflowSafety           ExecutionSandbox
  pattern blocking         syscall filtering
```

No v4 code exists. The architecture is designed so v4 adapters plug into AgentFactory's `execute_task()` method without changing governance/lock/merge layers.

## 8. Test Coverage

174 workflow-related tests across unit and integration:

- `tests/unit/test_agent_factory.py` -- task creation, deps, planning, 3 modes
- `tests/unit/test_governance_state.py` -- transitions, closeout, validation
- `tests/unit/test_worker_pool.py` -- assign, release, capacity
- `tests/unit/test_workflow_loader.py` -- YAML load, validation, normalization
- `tests/unit/test_workflow_safety.py` -- forbidden patterns, transitions, frozen access
- `tests/unit/test_component_ownership.py` -- register, conflict, release
- `tests/unit/test_workflow_lock_manager.py` -- acquire, release, reentrant, force
- `tests/unit/test_merge_review.py` -- propose, accept, reject, conflict detection
- `tests/unit/test_workflow_templates.py` -- template access, required fields
- `tests/integration/test_workflow_runtime_e2e.py` -- full lifecycle: queue/dag/closeout modes, safety blocks, worker recycling, governance state lifecycle, phase2 simulation
- `tests/integration/test_multi_agent_collision.py` -- merge review conflict, accept updates canonical, full governance flow

Total project: 2056 tests collected.
