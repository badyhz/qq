# Agent Handoff Envelope Specification

## Overview

The agent handoff envelope defines the contract for delegating work to a sub-agent. It specifies what the agent may do, what it must not do, what tests to run, and how to commit.

## Data Models

### AgentHandoffEnvelope

| Field | Type | Description |
|-------|------|-------------|
| envelope_id | str | Unique identifier |
| mission_summary | str | Brief description of the mission |
| allowed_scope | Tuple[str, ...] | Paths/modules the agent may touch |
| forbidden_paths | Tuple[str, ...] | Paths the agent must not touch |
| test_commands | Tuple[str, ...] | Commands to run for validation |
| commit_rules | Tuple[str, ...] | Commit message/format rules |
| safety_constraints | Tuple[str, ...] | Additional safety constraints |

### AgentHandoffSafetyRule

| Field | Type | Description |
|-------|------|-------------|
| rule_id | str | Unique identifier |
| rule_type | str | FORBIDDEN_PATH / FORBIDDEN_ACTION / REQUIRED_CHECK |
| description | str | Human-readable description |
| severity | str | CRITICAL / WARNING |

### AgentHandoffTestSpec

| Field | Type | Description |
|-------|------|-------------|
| spec_id | str | Unique identifier |
| test_command | str | Command to execute |
| expected_result | str | Expected outcome |
| timeout_seconds | int | Max wait time |
| mandatory | bool | Whether test must pass |

### AgentHandoffCommitRule

| Field | Type | Description |
|-------|------|-------------|
| rule_id | str | Unique identifier |
| pattern | str | Required commit message pattern |
| description | str | Human-readable description |
| required | bool | Whether rule is mandatory |

### AgentHandoffVerdict

| Field | Type | Description |
|-------|------|-------------|
| verdict | str | PASS / FAIL / WARN |
| notes | str | Summary notes |
| violations | Tuple[str, ...] | List of violations |
| warnings | Tuple[str, ...] | List of warnings |

## Verdict Logic

- CRITICAL safety rules produce FAIL violations
- WARNING safety rules produce WARN warnings
- Missing mandatory test commands produce FAIL violations
- Missing required commit rule patterns produce FAIL violations
- No violations + no warnings = PASS
- No violations + warnings = WARN
- Any violations = FAIL

## Renderer Functions

All rendering is pure markdown string generation:

- `render_handoff_envelope_md` — full envelope markdown
- `render_safety_rule_md` — table row for a safety rule
- `render_test_spec_md` — table row for a test spec
- `render_commit_rule_md` — table row for a commit rule
- `render_handoff_verdict_md` — verdict with violations/warnings sections
