# Frozen Backlog Evidence Requirement

**Task:** T1267
**Status:** release_hold = HOLD
**Scope:** All 22 frozen backlog files

## Purpose

Define evidence artifacts required before any frozen file
may be considered for promotion out of HOLD state.

## Required Evidence Per File

### 1. Static Analysis Report
- Import map (all dependencies)
- Function/class inventory
- External call surface (network, file, subprocess)
- Credential access patterns (env vars, config reads)

### 2. Side-Effect Audit
- Network endpoints contacted
- File paths written to
- Subprocess commands spawned
- Environment variables accessed
- State mutations attempted

### 3. Risk Classification Confirmation
- HIGH or MEDIUM classification
- Justification for classification
- Comparison to similar tracked files
- Escalation triggers identified

### 4. Dry-Run Compatibility Assessment
- Can file run in dry-run mode?
- What does dry-run mode skip?
- What side effects remain in dry-run?
- Is dry-run mode safe for CI?

### 5. Rollback Plan
- How to revert if promotion causes issues
- Dependencies that would break on rollback
- Data/state that would be orphaned

## Evidence Packet Structure

```
EVIDENCE_PACKET: <filename>
STATIC_ANALYSIS: <artifact_path>
SIDE_EFFECTS: <artifact_path>
RISK_CLASS: <classification>
DRY_RUN: <assessment>
ROLLBACK: <plan_path>
COMPLETENESS: <percentage>
```

## Incomplete Evidence

- Incomplete evidence = automatic HOLD
- No partial promotion allowed
- Missing artifacts must be generated before review
