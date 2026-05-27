# Read-Only Hook Rollout Hold Packet

## Purpose

Define the rollout hold mechanism for the read-only hook system. A rollout hold prevents any deployment, activation, or live integration of the read-only hook until explicit human approval is granted.

## Contract

The rollout hold is a gate object that blocks all downstream actions. It must be present and active before any read-only hook code is considered deployable. The hold is immutable without human intervention.

## Fields / Items

| Field | Value | Description |
|-------|-------|-------------|
| `hold_active` | `True` | Hold is currently enforced |
| `scope` | `read-only-hook` | Applies to all read-only hook components |
| `reasons` | `[design-only, no-live-auth, human-review-required]` | Why the hold exists |
| `created_at` | T961-T980 design phase | When hold was established |
| `release_condition` | human-approval-only | What must happen to release |

## Rules

1. Hold cannot be released without human approval.
2. No automated process, agent, or script may set `hold_active = False`.
3. Any attempt to bypass the hold must be logged and blocked.
4. The hold applies to all environments: dev, test, staging, production.
5. Hold status must be checked before any hook execution is attempted.

## Safety

- Default state is always `hold_active = True`.
- If hold status is missing or unreadable, treat as active.
- No code path may assume the hold is released.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
