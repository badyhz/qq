# Dirty Workspace Classification Policy

## Purpose

Define how workspace files are classified into categories for governance decisions.

## Categories

### A — Route

**Criteria:** File lives in `automation/` or matches route-related patterns. Contains routing logic, dispatch, or signal path definitions.

**Risk default:** MEDIUM

### B — Runtime / Live

**Criteria:** File contains live execution logic, exchange interaction, order submission, or runtime orchestration. Includes files in `core/` with execution/submit/live semantics.

**Risk default:** HIGH

### C — Docs / Readiness

**Criteria:** File lives in `docs/` and contains readiness assessments, closeout bundles, or state documentation.

**Risk default:** LOW

### D — Tests

**Criteria:** File lives in `tests/` or filename starts with `test_`. Contains test logic, fixtures, or assertions.

**Risk default:** LOW

### E — Scripts

**Criteria:** File lives in `scripts/`. Contains automation, pipeline, or operational scripts.

**Risk default:** MEDIUM

### F — Safe / Unrelated

**Criteria:** File has no trading, runtime, or risk content. Includes config templates, gitignore, requirements.txt, non-sensitive utilities.

**Risk default:** LOW

### G — Human Decision Required

**Criteria:** File cannot be automatically classified. Ambiguous content, mixed signals, or unknown path.

**Risk default:** HIGH (conservative)
