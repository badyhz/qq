# Governance Operating Layer Overview

## Purpose

The governance operating layer provides agent handoff envelopes, release hold dashboards, and closeout reporting for the T1361-T1440 batch.

## Components

### Agent Handoff Envelope (T1391-T1396)

- **AgentHandoffEnvelope** — frozen dataclass defining mission scope, forbidden paths, test commands, commit rules, safety constraints
- **AgentHandoffSafetyRule** — frozen dataclass for safety rules (FORBIDDEN_PATH, FORBIDDEN_ACTION, REQUIRED_CHECK)
- **AgentHandoffTestSpec** — frozen dataclass for test requirements with timeout and mandatory flag
- **AgentHandoffCommitRule** — frozen dataclass for commit pattern constraints
- **AgentHandoffVerdict** — frozen dataclass for pass/fail/warn verdict with violations and warnings
- **build_verdict** — pure function to evaluate constraints and produce a verdict
- **Renderer functions** — pure markdown rendering for all handoff models

### Release Hold Dashboard (T1397-T1398)

- **ReleaseHoldDashboard** — frozen dataclass showing hold status, frozen/medium counts, governance layers, next human action
- **Renderer functions** — pure markdown rendering for dashboard

## Constraints

- All classes are frozen dataclasses
- All functions are pure (no I/O, no network, no random, no timestamps, no env reads)
- Release hold status: HOLD
- No live trading, no exchange connectors, no secret management

## Test Coverage

- test_agent_handoff_envelope.py: 17 tests
- test_release_hold_dashboard.py: 9 tests
