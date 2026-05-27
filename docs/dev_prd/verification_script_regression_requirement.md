# Verification Script Regression Requirement

**Task ID:** T1286
**release_hold:** HOLD
**Status:** Active

## Policy

Every verification script must have regression test coverage before promotion.

## Minimum Requirements

1. **Positive case** — Script passes when target condition is true
2. **Negative case** — Script fails (non-zero exit) when target condition is false
3. **Edge case** — Script handles empty/missing input gracefully
4. **Idempotency** — Running script twice produces identical results

## Test File Convention

- Test file: `tests/unit/test_verify_<script_name>.py`
- Test class: `TestVerify<ScriptName>`
- Each test must be runnable in isolation

## Coverage Thresholds

- Line coverage >= 80% for the verification script
- All branch paths covered (if/else, try/except)
- All exit codes exercised at least once

## Promotion Gate

- No regression tests = BLOCK promotion
- Coverage below 80% = HOLD promotion
- All tests green = eligible for human confirmation (T1287)
