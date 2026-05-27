# Real Adapter Readiness Assessment (T726)

## 1. Current State

### What Exists

| Component | File | Status |
|---|---|---|
| AgentAdapter ABC | `core/agent_adapter.py` | Sync-only, 5 abstract methods: `adapter_id`, `submit_task`, `poll`, `cancel`, `status` |
| MockAdapter | `core/agent_adapter.py` | Working. In-memory dict, no API calls, auto-complete mode. |
| ClaudeAdapter | `core/agent_adapter.py` | Stub. All methods raise NotImplementedError. |
| MiMoAdapter | `core/agent_adapter.py` | Stub. All methods raise NotImplementedError. |
| CodexAdapter | `core/agent_adapter.py` | Stub. All methods raise NotImplementedError. |
| AdapterSafetyBoundary | `core/adapter_safety.py` | Keyword-based classification. Blocks LIVE_TRADING + RUNTIME_ORCHESTRATION. No cost/timeout circuit breakers. |
| WorkflowLockManager | `core/workflow_lock_manager.py` | In-memory locks. No persistence. No TTL/stale detection. |
| ComponentOwnershipRegistry | `core/component_ownership.py` | In-memory. Same limitations as lock manager. |
| MergeReviewPipeline | `core/merge_review.py` | Hash-based conflict detection. No auto-resolve, no rollback. |
| WorkflowRuntime | `core/workflow_runtime.py` | Sync scheduler. Connects safety + governance. No async path. |

### Safety Boundary Current Capabilities
- Allowed: SAFE_READONLY, SIMULATION, GUARD_INJECTION
- Blocked: HIGH_RISK_WRITE (frozen patterns), LIVE_TRADING, RUNTIME_ORCHESTRATION
- Validation: prompt keyword scoring + frozen pattern matching
- Missing: cost limits, API failure circuit breakers, execution timeouts

---

## 2. Claude Adapter Readiness

### API Abstraction Needed
- Anthropic Messages API (not legacy Completions)
- Streaming support required (SSE events)
- Token usage in response headers (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`)
- Tool use / tool_choice support for agentic workflows

### Authentication
- API key via `ANTHROPIC_API_KEY` env var (current project convention)
- Optional: OAuth for claude.ai Code (if targeting that path)
- Key rotation: adapter must not hardcode, must re-read env or accept config injection

### Rate Limiting
- Anthropic rate limits: requests/min, tokens/min vary by tier
- Must handle 429 responses with retry-after headers
- Token bucket or sliding window limiter needed
- Burst capacity: Claude API supports short bursts but sustained high throughput needs backoff

### Cost Tracking
- Track `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` per request
- Compute cost per request (model-dependent pricing)
- Accumulate per-session and per-workflow cost
- Alert at configurable thresholds (soft limit = warning, hard limit = halt)

### Stop Conditions
- Cost exceeds budget cap
- Token limit hit mid-request (max_tokens exceeded)
- Repeated 429/5xx errors (circuit breaker after N failures)
- Prompt injection detected (safety boundary escalation)
- Adapter runtime exceeds timeout (stuck request)

---

## 3. MiMo Adapter Readiness

### API Abstraction Needed
- Depends on MiMo deployment target (self-hosted, cloud API, or SDK)
- If cloud API: likely OpenAI-compatible or custom REST
- If self-hosted: gRPC or HTTP endpoint with model-specific parameters
- Streaming support: likely SSE or chunked HTTP

### Authentication
- Model-specific: API key, bearer token, or mTLS for self-hosted
- Key management: same env-var pattern as Claude

### Rate Limiting
- Self-hosted: no external rate limits, but GPU inference has throughput ceiling
- Cloud: similar to Claude but different limits per provider
- Must detect 503 (model overloaded) separately from 429 (rate limit)

### Cost Tracking
- Self-hosted: track GPU time, not token cost
- Cloud: token-based pricing (different from Claude)
- Unified cost model: abstract to "cost units" with per-adapter conversion

### MiMo-Specific Considerations
- Context window may differ from Claude (check model docs)
- Tool use support may be limited or different schema
- Response format may not match Claude's structure -- adapter must normalize to TaskResult
- Model versioning: MiMo has multiple versions, adapter must specify model ID

---

## 4. Codex Adapter Readiness

### API Abstraction Needed
- OpenAI API format (Codex is OpenAI model line)
- Chat completions endpoint with code-specific parameters
- Streaming required for real-time progress

### Authentication
- `OPENAI_API_KEY` env var
- Organization/project headers for billing attribution

### Rate Limiting
- OpenAI tiered rate limits (RPM, TPM, IPM)
- Must handle `Retry-After` header on 429
- Batch API available for non-time-sensitive tasks (lower cost, async)

### Cost Tracking
- Token-based: input + output + cached tokens
- Model-dependent pricing (codex-mini vs older models)
- Same "cost units" abstraction as MiMo

### Codex-Specific Considerations
- Code execution sandbox: Codex may execute code -- needs separate safety boundary
- File system access: Codex adapters may write files, conflicting with lock manager
- Response includes `finish_reason` -- must map to AdapterStatus correctly
- `tool_calls` for function calling -- different format from Claude's tool_use

---

## 5. Governance Gaps

### Real File Locking
- Current: `WorkflowLockManager` is in-memory dict. Lost on process restart.
- Needed: File-system locks (fcntl/flock) or Redis-based distributed locks for multi-process.
- Stale lock detection: locks must have TTL. If holder crashes, lock must auto-expire.
- Cross-agent locking: two real adapters may run in separate processes.

### Actual Merge Conflicts
- Current: `MergeReviewPipeline` uses hash comparison only. No content-level diff.
- Needed: Unified diff generation for code files. Three-way merge support.
- Conflict resolution: auto-merge for non-overlapping changes, human review for conflicts.
- Git integration: real adapters modifying code should produce diffs reviewable via `git diff`.

### Rollback Mechanisms
- Current: none. Accepted MRs update canonical hash, no undo.
- Needed: Snapshot before modification. Rollback to snapshot on failure.
- Git-based: `git stash`, `git checkout -- <file>`, or branch-based rollback.
- Transactional: all-or-nothing for multi-file changes.

---

## 6. Safety Gaps

### Real-Time Safety Monitoring
- Current: `AdapterSafetyBoundary` validates before submission only. No runtime monitoring.
- Needed: Watchdog thread/process monitoring adapter execution.
- Anomaly detection: unexpected file writes, network calls, process spawning.

### Circuit Breakers for API Failures
- Current: none.
- Needed: Per-adapter circuit breaker with three states: CLOSED (normal), OPEN (blocked), HALF-OPEN (testing).
- Trigger: N consecutive failures within M seconds.
- Recovery: exponential backoff, then probe with single request.

### Budget/Cost Limits
- Current: none.
- Needed: Per-request cost cap, per-session cost cap, per-workflow cost cap.
- Enforcement: check before submission, abort if exceeded.
- Alerts: log warning at 80% budget, halt at 100%.

### Execution Timeout Handling
- Current: `poll()` is sync with no timeout. Can block indefinitely.
- Needed: Configurable timeout per adapter call. `asyncio.wait_for` or `threading.Timer`.
- Timeout response: cancel task, release locks, mark as FAILED.

---

## 7. API Abstraction Changes

### Async Support
- Current ABC is fully synchronous.
- Real adapters MUST be async (HTTP calls, streaming).
- Options:
  - (A) Add `async def` methods to ABC, implement sync wrappers for MockAdapter.
  - (B) New `AsyncAgentAdapter` ABC, keep existing for backward compat.
- Recommendation: Option (B) -- additive, no breaking change to MockAdapter.

### Streaming Response Handling
- `submit_task` currently returns a request_id (fire-and-forget).
- Streaming needs: callback for partial responses, or async iterator.
- TaskResult would need optional `stream_chunks` field.
- Backward compat: MockAdapter returns None for stream_chunks.

### Retry Logic
- Current: no retry anywhere.
- Needed: configurable retry policy per adapter (max retries, backoff, retryable status codes).
- Must not retry non-idempotent operations (e.g., order submission in live trading).
- Retry decorator or middleware pattern.

### Error Classification
- Current: exceptions are unstructured.
- Needed: typed errors per adapter.
  - `RateLimitError` (retryable, backoff)
  - `AuthenticationError` (non-retryable, halt)
  - `ServerError` (retryable, limited)
  - `CostLimitError` (non-retryable, halt)
  - `TimeoutError` (retryable, once)
  - `SafetyViolation` (non-retryable, halt + alert)

---

## 8. Recommended Stop Conditions

### When to Pause Real Adapter Execution
- Safety boundary escalation: any task classified as LIVE_TRADING
- Cost budget exceeded
- Consecutive API failures > threshold (circuit breaker open)
- Lock held longer than TTL (stale lock detected)
- Merge conflict detected with no auto-resolve path
- Human-in-the-loop queue has pending approvals

### Human-in-the-Loop Requirements
- First real adapter execution: manual approval required
- Any change to frozen patterns: manual approval
- Cost threshold breach: human notification + pause
- New adapter type registration: manual review
- Rollback after failed merge: human confirmation

### Automatic Rollback Triggers
- Adapter timeout exceeded
- Safety violation during execution (not just pre-check)
- Lock acquisition failure after retry
- API returns data corruption / invalid response format
- File hash mismatch after write (integrity check failure)

---

## 9. Roadmap Recommendation

### Phase 1: Single Real Adapter (Claude)
- Implement ClaudeAdapter with async HTTP client
- Add cost tracking + budget enforcement
- Add circuit breaker (simple: 3 failures = open, 60s cooldown)
- Add execution timeout (30s default)
- Extend AdapterSafetyBoundary with cost/timeout categories
- Keep MockAdapter working, add AsyncAgentAdapter ABC
- Test with read-only tasks first, then guard injection

### Phase 2: Multi-Adapter with Failover
- Implement MiMoAdapter (or CodexAdapter, pick one)
- Add adapter registry (name -> adapter, priority, health)
- Add failover logic: if primary fails, route to secondary
- Unified cost model across adapters
- File-system locking for multi-process scenarios
- Git-based rollback for file modifications

### Phase 3: Autonomous Multi-Agent
- All three adapters operational
- Adapter selection based on task type + cost + health
- Full governance pipeline: propose -> review -> merge -> verify
- Distributed lock manager (Redis or similar)
- Real-time monitoring dashboard
- Autonomous rollback with human escalation

### Phase 0.5 (Immediate Prerequisite)
- Add async ABC without breaking MockAdapter
- Add cost tracking dataclass to TaskResult
- Add error classification enum
- Add circuit breaker class (adapter-agnostic)
- Add timeout wrapper utility

---

## Summary

| Area | Current | Required for Real |
|---|---|---|
| ABC interface | Sync only | Async + sync bridge |
| Auth | Not implemented | Env-var based, per-adapter |
| Rate limiting | None | Per-adapter limiter |
| Cost tracking | None | Per-request + cumulative |
| Circuit breaker | None | Per-adapter, 3-state |
| Timeout | None | Configurable per-call |
| File locking | In-memory | Persistent + TTL |
| Merge conflicts | Hash only | Diff + 3-way merge |
| Rollback | None | Snapshot + restore |
| Error types | Unstructured | Typed classification |
