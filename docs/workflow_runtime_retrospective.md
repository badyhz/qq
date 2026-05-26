# Workflow Runtime Retrospective

**Date**: 2026-05-27
**Scope**: Workflow runtime system v1 through governance wave
**Result**: Runtime simulation complete, governance layer proven, 164 tests passing

---

## 1. What Was Built

### v1 -- Orchestration Skeleton
- `core/agent_factory.py`: ExecutionMode enum (DAG, QUEUE, CLOSEOUT), Task dataclass, TaskStatus, AgentFactory with slot-based dispatch
- `core/worker_pool.py`: Slot-based concurrency tracker (WorkerPool, Worker, WorkerState). Canonical version created in T707.
- Simulation only -- no real threads, no real agents

### v2 -- Governance State Machine
- `core/governance_state.py`: Formal lifecycle state machine (NEW -> READY -> RUNNING -> PASS/FAIL/PARTIAL -> CLOSED). Valid transition map enforced.
- `core/workflow_runner.py`: Connects agent_factory, governance_state, and workflow_templates. Builds workflows from task spec dicts.
- `automation/workflow_templates.py`: Template definitions with parallel_policy.mode routing

### v3 -- Coordination Layer
- `core/component_ownership.py`: ComponentOwnershipRegistry -- prevents concurrent writes via exclusive/shared permission model. Raises ConflictError on double-ownership.
- `core/workflow_lock_manager.py`: WorkflowLockManager -- exclusive locks per component path, reentrant for same task, LockError on conflict.
- `core/merge_review.py`: MergeReviewPipeline -- propose/review/accept/reject flow with canonical vs candidate hash comparison. Conflict status when hashes diverge.

### Governance Wave -- Safety and Scheduling
- `core/workflow_safety.py`: Safety gates (kill-switch checks, mode validation) integrated into workflow execution
- `core/workflow_scheduler.py`: Task scheduling with dependency resolution
- `core/workflow_status.py`: Status tracking and reporting
- `core/workflow_loader.py`: Workflow definition loading from templates/specs
- `core/audit_log.py`: Audit trail for governance actions

### Test Coverage
- 12 workflow-specific test files in `tests/unit/`:
  - `test_worker_pool.py`
  - `test_workflow_runner.py`
  - `test_workflow_safety.py`
  - `test_workflow_scheduler.py`
  - `test_workflow_status.py`
  - `test_workflow_loader.py`
  - `test_workflow_lock_manager.py`
  - `test_workflow_cli.py`
  - `test_workflow_cli_runtime.py`
  - `test_workflow_templates.py`
  - `test_governance_state.py`
  - `test_agent_factory.py`
- 164 tests across the workflow runtime system

---

## 2. What Worked Well

### Parallel Agent Execution
DAG mode proved effective for independent tasks. Multiple agents could operate concurrently without conflict when targeting different files. The 5-agent standard limit balanced throughput against context management.

### Simulated Orchestrator First
Building simulation-only components (WorkerPool, AgentFactory, GovernanceStateMachine) before introducing real adapters was the right call. It exposed design flaws cheaply -- the T707/T710 collision happened in simulation, not in production.

### State Machine Enforcement
The formal transition map in governance_state.py caught invalid state progressions at test time. No task could skip states or transition illegally. This prevented silent drift.

### Template-Driven Workflows
Workflow templates encoded parallelism rules (QUEUE vs DAG vs CLOSEOUT) declaratively. The runner resolved mode automatically. This separated "what to do" from "how to execute it."

---

## 3. The T707/T710 Collision Incident

### Timeline
- **T707**: Created canonical `core/worker_pool.py` -- full implementation with WorkerPool, Worker, WorkerState, TaskAssignment, assign/complete/status methods
- **T710**: Ran in parallel, overwrote `core/worker_pool.py` with a simpler version during its own execution
- **Result**: Canonical implementation lost. T707's work was silently destroyed.

### Root Cause
No coordination layer existed between parallel tasks. Both tasks had write access to the same file path. Nothing prevented T710 from clobbering T707's output because:
1. No file lock mechanism
2. No component ownership registry
3. No merge review pipeline
4. Tasks were launched in parallel without checking file-target overlap

### Impact
- Canonical worker_pool.py replaced with simpler version
- Tests passed (simpler version was functional) but design intent was lost
- Exposed the fundamental gap: simulation-only runtime had no protection against concurrent writes

### Resolution
T707 was re-executed to restore the canonical version. The collision directly motivated the v3 coordination layer.

---

## 4. Why Governance Layer Was Needed

### Ownership
`ComponentOwnershipRegistry` tracks which task owns which component path. Second task attempting to register same path gets ConflictError. Prevents the T707/T710 scenario structurally.

### Locks
`WorkflowLockManager` provides exclusive locks per component. Same task can re-acquire (reentrant). Different task gets LockError. Ensures atomic write access.

### Merge Review
`MergeReviewPipeline` forces explicit review when changes conflict. Canonical hash vs candidate hash comparison detects drift. REJECTED or CONFLICT status prevents blind overwrites.

### Why Simulation-Only Was Not Enough
The T707/T710 collision proved that "simulation only" is not a safety guarantee. Even without real agents, parallel task execution can destroy work. Governance must exist at the coordination layer, not just the execution layer.

---

## 5. Why Real Agent Adapters Are Deferred

### Coordination Must Come First
Real agents (Claude, MiMo) introduce non-deterministic execution timing. Without proven coordination:
- Two agents could lock the same component simultaneously
- Merge review could be bypassed by agent error
- Ownership registry could become stale if agents crash mid-task

### Simulation Proved the Pattern
The governance layer was validated in simulation. Real agents would add:
- Actual subprocess management
- Real API calls to LLM providers
- Timeout and retry logic
- Context window management

These are runtime concerns, not governance concerns. Governance must be stable before runtime complexity is added.

### Risk Assessment
| Concern | Simulation | Real Agents |
|---------|-----------|-------------|
| File collision | T707/T710 caught | Would happen at speed |
| State machine | Enforced in tests | Must enforce at runtime |
| Lock contention | No real contention | Real concurrency |
| Merge conflicts | Synthetic | Real code changes |

---

## 6. Next Recommended Roadmap

### Runtime v4: Real Agent Adapters
After governance is proven in production-like simulation:
- Claude adapter: spawn Claude Code instances as execution workers
- MiMo adapter: spawn MiMo instances for specific task types
- Both must respect governance layer (ownership, locks, merge review)
- Adapter must call governance APIs before any file write

### Governance Hardening: Real File Locks
If moving beyond simulation:
- Filesystem-level locks (flock/fcntl) as backup to in-memory locks
- Lock timeout and stale lock recovery
- Distributed lock coordination if running across machines
- Atomic file writes (write-to-temp, rename) to prevent partial corruption

### Integration with Execution Guard System
- Governance state machine should feed into execution guard reports
- Component ownership should be reflected in guard schema
- Merge review status should appear in governance board
- Lock contention events should be logged in audit trail

### Phase Alignment
| Phase | Scope | Prerequisite |
|-------|-------|-------------|
| Runtime v4 | Real agent adapters | Governance proven |
| Governance hardening | Real file locks | Beyond simulation |
| Guard integration | Governance + execution guard | Both systems stable |

---

## Conclusion

The workflow runtime evolved from simple orchestration (v1) through formal state management (v2) to a coordination layer (v3) forced by the T707/T710 collision. The governance layer -- ownership, locks, merge review -- is the structural answer to "what prevents parallel agents from destroying each other's work." Real agent adapters are deferred until this coordination is proven. The 164-test simulation runtime is the safe proving ground.
