# T2201-T2600 Safe Fix Log

## Fix 1: Replace asyncio.get_event_loop() with asyncio.run()

**Commit:** 7abf4db
**Files modified:** 16 test files
**Change:** Replaced all `asyncio.get_event_loop().run_until_complete(...)` with `asyncio.run(...)`.

**Why safe:**
- Test-only change
- `asyncio.run()` is the correct API for Python 3.10+
- No implementation code touched
- No frozen files touched

**Files:**
1. tests/unit/test_async_agent_adapter.py
2. tests/unit/test_mimo_api_adapter.py
3. tests/unit/test_mimo_sandbox_adapter.py
4. tests/unit/test_transport_benchmark.py
5. tests/unit/test_transport_circuit_breaker.py
6. tests/unit/test_transport_dedup.py
7. tests/unit/test_transport_headers.py
8. tests/unit/test_transport_health.py
9. tests/unit/test_transport_integration_matrix.py
10. tests/unit/test_transport_metrics.py
11. tests/unit/test_transport_middleware.py
12. tests/unit/test_transport_observability.py
13. tests/unit/test_transport_retry.py
14. tests/unit/test_transport_sandbox.py
15. tests/unit/test_transport_timeout.py
16. tests/unit/test_workflow_runtime_async.py

**Result:** 110 failures fixed (61 transport + 45 MiMo + 4 workflow runtime).

## Fix 2: Set cwd and QQ_RUNTIME_MODE in subprocess tests

**Commit:** 020098b
**Files modified:** 10 test files
**Change:** Set `cwd` to project root and pass `QQ_RUNTIME_MODE=dry-run` in subprocess invocations.

**Why safe:**
- Test-only change
- Subprocess calls now correctly find project modules
- Environment variable ensures dry-run mode
- No implementation code touched
- No frozen files touched

**Files:**
1. tests/unit/test_t412_real_ohlcv_source_schema_audit.py
2. tests/unit/test_t413_real_ohlcv_source_mapping.py
3. tests/unit/test_t416_real_ohlcv_gap_candidates.py
4. tests/unit/test_t420_ohlcv_gap_validation_control_report.py
5. tests/unit/test_t421_ohlcv_gap_manual_review_packet.py
6. tests/unit/test_t422_ohlcv_gap_manual_review_checklist_interpreter.py
7. tests/unit/test_t423_ohlcv_gap_manual_approval_artifact.py
8. tests/unit/test_t424_ohlcv_gap_manual_approval_gate_report.py
9. tests/unit/test_t425_ohlcv_gap_manual_review_phase_control_report.py
10. tests/unit/test_t497_human_confirmation_token_gate.py

**Result:** 10 failures fixed (7 OHLCV gap + 1 human confirmation + 2 OHLCV approval reports).

## Commit Summary

| Commit | Description | Files | Failures Fixed |
|--------|-------------|-------|----------------|
| 7abf4db | Replace deprecated asyncio.get_event_loop() in all test files | 16 | 110 |
| 020098b | Stabilize OHLCV gap and human confirmation token CLI tests | 10 | 10 |

## Safety Invariants Maintained

- Zero implementation files modified
- Zero frozen files touched
- All 22 frozen files remain untouched
- Release hold: HOLD (unchanged)
