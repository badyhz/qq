# Workflow Runtime Stack v4 -- Architecture Freeze

Date: 2026-05-27 (T724)

## 1. Stack Versions

### v1 -- Engine Core (commit 51b3917)
Task graph + slot tracker.

| Component | File | Role |
|---|---|---|
| AgentFactory | `core/agent_factory.py` | Task graph: QUEUE (sequential), DAG (parallel waves), CLOSEOUT (7-step verification). Plans execution waves. |
| WorkerPool | `core/worker_pool.py` | Slot-based concurrency tracker. N workers, assign/release/status. Simulation only -- no real threads. |
| WorkflowLoader | `core/workflow_loader.py` | Loads YAML or Python dict templates from `automation/workflow_templates/`. Validates required fields. |
| WorkflowSafetyValidator | `core/workflow_safety.py` | Policy gate. Blocks forbidden task patterns, forbidden modes, frozen file access, invalid state transitions. |

### v2 -- Orchestration
Template-driven workflow execution.

| Component | File | Role |
|---|---|---|
| WorkflowRunner | `core/workflow_runner.py` | Connects agent_factory + governance_state + templates. Builds tasks, computes plan, simulates execution. |
| WorkflowScheduler | `core/workflow_scheduler.py` | Step-by-step scheduler. Resolves ready tasks, assigns to WorkerPool, transitions governance state. |

### v3 -- Governance Layer
Multi-agent collision prevention.

| Component | File | Role |
|---|---|---|
| GovernanceStateMachine | `core/governance_state.py` | 8-state lifecycle: NEW -> READY -> RUNNING -> PASS/PARTIAL/FAIL -> CLOSED. Enforces valid transitions. |
| WorkflowLockManager | `core/workflow_lock_manager.py` | Exclusive locks per component path. Reentrant for same task. force_release for admin. |
| ComponentOwnershipRegistry | `core/component_ownership.py` | Registers owner_task per component_path. exclusive/shared permission. ConflictError on cross-task writes. |
| MergeReviewPipeline | `core/merge_review.py` | MR lifecycle: proposed -> reviewing -> accepted/rejected. Auto-conflict on hash divergence. |

### v4 -- Adapter Boundary (frozen, no live execution)
Agent adapter contracts + safety boundary.

| Component | File | Role |
|---|---|---|
| AgentAdapter (ABC) | `core/agent_adapter.py` | Abstract contract: submit_task, poll, cancel, status. |
| MockAdapter | `core/agent_adapter.py` | Simulated adapter. No real API calls. |
| ClaudeAdapter | `core/agent_adapter.py` | Stub. All methods raise NotImplementedError. |
| MiMoAdapter | `core/agent_adapter.py` | Stub. All methods raise NotImplementedError. |
| CodexAdapter | `core/agent_adapter.py` | Stub. All methods raise NotImplementedError. |
| AdapterSafetyBoundary | `core/adapter_safety.py` | Task classification + forbidden pattern enforcement. Allowed categories: SAFE_READONLY, SIMULATION, GUARD_INJECTION. |
| MockAgentSwarm | `core/mock_agent_swarm.py` | Simulated multi-agent swarm. Uses MockAdapter. Supports autopilot dispatch. |
| WorkflowRuntime | `core/workflow_runtime.py` | Unified runtime: scheduler + safety + governance in one entry point. |

## 2. Architecture Diagram

```
+------------------------------------------------------------------+
|  Layer 4 -- CLI / Entry Points                                    |
|  scripts/workflow_cli.py, scripts/workflow_status.py              |
+------------------------------------------------------------------+
         |
+------------------------------------------------------------------+
|  Layer 3 -- Orchestration                                         |
|  WorkflowRunner         WorkflowScheduler        WorkflowRuntime  |
|  (template-driven)     (step-by-step dispatch)   (unified entry) |
+------------------------------------------------------------------+
         |                        |
+------------------------------------------------------------------+
|  Layer 2 -- Governance                                            |
|  GovernanceStateMachine  WorkflowLockManager                      |
|  (8-state lifecycle)     (exclusive locks)                        |
|  ComponentOwnershipRegistry  MergeReviewPipeline                  |
|  (collision prevent)          (conflict detect + resolve)         |
+------------------------------------------------------------------+
         |
+------------------------------------------------------------------+
|  Layer 1 -- Engine                                                |
|  AgentFactory  WorkerPool  WorkflowLoader  WorkflowSafetyValidator|
|  (task graph)  (slots)     (YAML/Python)  (policy gate)          |
+------------------------------------------------------------------+
         |
+------------------------------------------------------------------+
|  Layer 0 -- Adapter Boundary (v4, simulation only)                |
|  AdapterSafetyBoundary  AgentAdapter(ABC)  MockAgentSwarm        |
|  (classify + block)     (stub contracts)   (sim swarm)           |
+------------------------------------------------------------------+
```

Data flow:

```
YAML/Python templates
        |
  WorkflowLoader (validate + load)
        |
  WorkflowRunner (build task graph)
   |         |
   v         v
AgentFactory  GovernanceStateMachine
 (waves)      (state machine)
   |         |
   v         v
WorkerPool    WorkflowLockManager
 (slots)      (exclusive access)
                  |
           ComponentOwnershipRegistry
             (who owns what)
                  |
            MergeReviewPipeline
             (conflict detect + resolve)
                  |
  AdapterSafetyBoundary (classify + block forbidden)
                  |
  WorkflowRuntime (unified entry, optional)
```

## 3. Hard Boundaries

### Simulation-Only
- Every core module docstring declares "Simulation only. No real agent execution."
- AgentFactory plans waves but never invokes external agents.
- WorkerPool tracks slots but creates no real threads/processes.
- WorkflowRunner.simulate_execution() hardcodes all tasks to PASS.

### No Real Adapter Calls
- `ClaudeAdapter`, `MiMoAdapter`, `CodexAdapter` are stubs.
- All methods raise `NotImplementedError`.
- Only `MockAdapter` is functional. It returns "mock output" without API calls.
- `MockAgentSwarm` dispatches to `MockAdapter` instances only.

### No Trading Integration
- `WorkflowSafetyValidator` blocks task patterns: `submit_order`, `cancel_order`, `flatten_position`, `live_mode`, `live_runner`.
- Forbidden modes: `LIVE_EXECUTION`, `REAL_TRADING`, `PLANNER_MODE`.
- 20 frozen script patterns blocked (live_runner, submit_approved, safe_flatten, etc.).
- `AdapterSafetyBoundary` classifies `LIVE_TRADING` and `RUNTIME_ORCHESTRATION` as forbidden categories.

### No live_runner Involvement
- `live_runner` appears in FORBIDDEN_TASK_PATTERNS (workflow_safety.py).
- `live_runner` appears in FROZEN_PATTERNS (workflow_safety.py).
- `live_runner` appears in _frozen_patterns (adapter_safety.py).
- `live_runner` appears in _CATEGORY_KEYWORDS mapped to RUNTIME_ORCHESTRATION (adapter_safety.py).

## 4. Safety Layers

### AdapterSafetyBoundary (`core/adapter_safety.py`)
- **Task classification**: Scores task_id + prompt against keyword sets per category (SAFE_READONLY, SIMULATION, GUARD_INJECTION, HIGH_RISK_WRITE, LIVE_TRADING, RUNTIME_ORCHESTRATION).
- **Forbidden patterns**: submit_order, cancel_order, place_order, close_position, open_position, binance_api, exchange_.
- **Frozen patterns**: live_runner, live_playbook, submit_approved, submit_replayed, safe_flatten, run_spot_testnet.
- **Allowed categories**: Only SAFE_READONLY, SIMULATION, GUARD_INJECTION by default.
- Raises `SafetyViolation` on forbidden requests.

### WorkflowSafetyValidator (`core/workflow_safety.py`)
- **FORBIDDEN_TASK_PATTERNS**: 7 patterns including live_runner, submit_order, cancel_order, flatten_position, runtime_integration, planner_integration, live_mode.
- **FORBIDDEN_MODES**: LIVE_EXECUTION, REAL_TRADING, PLANNER_MODE.
- **FROZEN_PATTERNS**: 20 script patterns that must never be written by tasks.
- **VALID_TRANSITIONS**: Formal state machine transition table validated at runtime.
- **validate_workflow()**: Checks mode, task IDs, dependency references, frozen exclusion.
- Severity levels: CRITICAL, HIGH, MEDIUM, LOW.

### GovernanceStateMachine (`core/governance_state.py`)
- **8-state lifecycle**: NEW -> READY -> RUNNING -> PASS/PARTIAL/FAIL/BLOCKED -> CLOSED.
- **Terminal states**: CLOSED (no further transitions).
- **Transition enforcement**: Invalid transitions raise ValueError.
- **History tracking**: Every transition recorded with reason.
- **Closeout verification**: can_closeout() checks all tasks are terminal or PASS.

### ComponentOwnershipRegistry (`core/component_ownership.py`)
- **Register**: exclusive or shared permission per component_path.
- **ConflictError**: Raised when different task tries to own same path.
- **Check**: Verifies requesting_task can write (owner, shared, or unowned).
- **Release**: Only owner can release ownership.

## 5. Test Coverage

221 tests across 18 test files:

- `tests/unit/test_agent_factory.py` -- task creation, deps, planning, 3 modes
- `tests/unit/test_governance_state.py` -- transitions, closeout, validation
- `tests/unit/test_worker_pool.py` -- assign, release, capacity
- `tests/unit/test_workflow_loader.py` -- YAML load, validation, normalization
- `tests/unit/test_workflow_safety.py` -- forbidden patterns, transitions, frozen access
- `tests/unit/test_component_ownership.py` -- register, conflict, release
- `tests/unit/test_workflow_lock_manager.py` -- acquire, release, reentrant, force
- `tests/unit/test_merge_review.py` -- propose, accept, reject, conflict detection
- `tests/unit/test_workflow_templates.py` -- template access, required fields
- `tests/unit/test_adapter_safety.py` -- classification, forbidden patterns, frozen exclusion
- `tests/unit/test_agent_adapter.py` -- adapter contract, mock behavior
- `tests/unit/test_mock_agent_swarm.py` -- swarm dispatch, scaling, autopilot
- `tests/unit/test_workflow_runtime.py` -- unified runtime entry
- `tests/unit/test_workflow_scheduler.py` -- step scheduling, worker assignment
- `tests/integration/test_workflow_runtime_e2e.py` -- full lifecycle: queue/dag/closeout modes
- `tests/integration/test_multi_agent_collision.py` -- merge review, ownership conflicts
- `tests/integration/test_workflow_safety_integration.py` -- safety boundary end-to-end
- `tests/integration/test_adapter_safety_integration.py` -- adapter safety with mock swarm

## 6. Release Tags

| Tag | Commit | Components |
|---|---|---|
| workflow-runtime-v1 | 51b3917 | AgentFactory, WorkerPool, WorkflowLoader, WorkflowSafetyValidator |

v2/v3/v4 components are committed but not tagged as separate releases. They build incrementally on v1.

## 7. Future v5 Boundary -- Real Adapter Integration

What would change if real adapters replaced stubs:

```
v1-v4 (current, frozen)        v5 (future, not committed)
MockAdapter only                ClaudeAdapter / MiMoAdapter / CodexAdapter
  return "mock output"            actual API calls via HTTP/SDK
WorkerPool (slot tracking)      ProcessPool / ThreadPool / asyncio
  simulation only                real concurrency + timeouts
WorkflowSafety (pattern block)  ExecutionSandbox
  deny-list filtering            syscall + network + filesystem sandbox
AdapterSafetyBoundary           RateLimiter + CostTracker
  category classification        per-adapter rate limits + cost caps
WorkflowRuntime                 LiveWorkflowRuntime
  simulation completion          async polling + retry + dead-letter
```

v5 requirements before any real adapter integration:
1. ExecutionSandbox with syscall filtering (not just pattern blocking).
2. RateLimiter per adapter (requests/min, tokens/min).
3. CostTracker with budget caps per workflow.
4. RetryPolicy with exponential backoff and dead-letter queue.
5. AuditLog with immutable append-only store.
6. CircuitBreaker per adapter (fail-open vs fail-closed configurable).
7. All 221 existing tests must pass unchanged after v5 adapter swap.

The architecture is designed so v5 adapters plug into AgentFactory.execute_task() without changing governance/lock/merge layers.
