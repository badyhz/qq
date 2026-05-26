# Runtime Dogfood Retrospective

**Date:** 2026-05-27
**Scope:** WorkflowRuntime v3 dogfood on quant workflow templates
**Status:** First real-use evaluation

---

## What worked

### 1. Template-driven execution is clean
Loading `SIGNAL_SCAN_PIPELINE` via `load_workflow()` → `WorkflowRuntime.run()` produces a complete execution trace with zero configuration. The template pack (7 templates) covers the actual quant workflow surface: scan, audit, docs sync, closeout.

### 2. DAG scheduling actually schedules
`WorkflowScheduler` correctly resolves dependencies and parallelizes independent tasks. `SIGNAL_SCAN_PIPELINE` (6 tasks) runs in 2 waves instead of 6 sequential steps. This is real parallelism, not simulated.

### 3. Observability events are structured and useful
Every task transition emits a typed event (`TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`). The `observability_summary()` gives a clean count-by-type without parsing logs. This is the right abstraction for debugging workflow failures.

### 4. Safety validation catches real issues
`WorkflowSafetyValidator` blocks forbidden task patterns (`submit_order`, `live_runner`) and frozen file access at load time, before any execution. The safety layer is cheap and effective.

### 5. Circuit breaker + retry compose correctly
The async execution path (`run_async()`) correctly trips the circuit breaker after repeated failures and enters HALF_OPEN for probing. Retry with exponential backoff works as designed. The two mechanisms are independent but compose cleanly.

---

## Where friction appeared

### 1. No task-level timeout
A stuck task blocks the entire workflow. The circuit breaker catches repeated failures but not hangs. Need per-task timeout in `run_async()` with adapter cancellation.

### 2. Budget tracking is manual
`record_budget()` must be called explicitly after each task. The runtime doesn't auto-track costs. For real orchestration, the adapter should report costs and the runtime should record them automatically.

### 3. Template format split (YAML vs Python dict)
`workflow_loader.py` tries YAML first, then Python dicts. Two formats for the same data is unnecessary complexity. Should converge on one.

### 4. No task output passing
Tasks can't read outputs from upstream tasks. `SIGNAL_SCAN_PIPELINE` has `fetch_market_data` → `compute_indicators`, but indicators can't access the fetched data. The runtime passes task IDs, not data. For real workflows, tasks need shared state or output channels.

### 5. Closeout template duplicates ENGINEERING_CLOSEOUT
`QUANT_CLOSEOUT_PIPELINE` is structurally identical to `ENGINEERING_CLOSEOUT`. Should be one template with parameterized phase name.

---

## What abstractions were missing

### 1. Task output / shared state
The runtime has no concept of task outputs flowing downstream. This is the biggest gap for real orchestration. Need either:
- A `TaskContext` dict passed through the DAG
- Output channels between tasks
- Or a shared store indexed by task_id

### 2. Conditional branching
All templates are linear DAGs. No `if signal_count > 0 then classify else skip`. Real quant workflows need conditional paths. The governance state machine supports `BLOCKED` state but the scheduler doesn't use it for conditional logic.

### 3. Task-level resource requirements
All tasks are equal. A `fetch_market_data` task might need network access while `aggregate_candidates` is pure computation. No way to express resource needs or constraints per task.

### 4. Workflow versioning
Templates have no version field. If `SIGNAL_SCAN_PIPELINE` changes, there's no way to know which version a running workflow used. Need `version: "1.0"` in template schema.

---

## What runtime assumptions failed

### 1. "All tasks complete synchronously"
The sync `run()` path assumes instant completion. The async path exists but isn't the default. For real adapters (API calls, model inference), sync is wrong. The runtime should default to async.

### 2. "Workers are fungible"
Worker pool treats all workers as identical. In reality, different adapters have different capabilities, costs, and reliability. A `ClaudeAdapter` worker is not interchangeable with a `MiMoAdapter` worker.

### 3. "Safety is load-time only"
Safety validation runs at `load_workflow()` time. But a workflow can be mutated after loading (tasks added/removed). Safety should be checked at schedule time, not just load time.

### 4. "One workflow at a time"
The runtime manages one workflow. Real usage needs concurrent workflows (scanning while auditing). The current design doesn't support multi-workflow isolation.

---

## What's required before real orchestration

### Must-have
1. **Task output passing** — tasks need to read upstream results
2. **Per-task timeout** — prevent stuck tasks from blocking
3. **Auto budget tracking** — adapter reports costs, runtime records
4. **Workflow versioning** — template version field
5. **Safety at schedule time** — not just load time

### Should-have
6. **Conditional branching** — if/else paths in DAG
7. **Worker specialization** — adapter-aware worker assignment
8. **Multi-workflow support** — concurrent workflow isolation
9. **Converge template format** — YAML only, deprecate Python dicts

### Nice-to-have
10. **Workflow persistence** — save/resume interrupted workflows
11. **Cost projections** — estimate total cost before execution
12. **Replay from checkpoint** — re-run from a specific task

---

## Conclusion

The runtime works as a simulation orchestrator. The core abstractions (scheduler, governance, safety, observability) are sound. The gaps are in data flow (task outputs), operational concerns (timeouts, budgets), and real-world complexity (conditional logic, worker specialization).

The dogfood validated that template-driven workflow execution is the right architecture. The next step is filling the "must-have" gaps before connecting real adapters.
