# Release Hold Dashboard Specification

## Overview

The release hold dashboard provides a frozen snapshot of the current governance status. It shows the hold status, file counts, governance layers, and the next required human action.

## Data Model

### ReleaseHoldDashboard

| Field | Type | Description |
|-------|------|-------------|
| dashboard_id | str | Unique identifier |
| hold_status | str | Always "HOLD" |
| frozen_count | int | Number of HIGH-risk frozen files |
| medium_count | int | Number of MEDIUM-risk governed files |
| governance_layers | Tuple[str, ...] | Names of active governance layers |
| next_human_action | str | Description of next required human action |

## Constraints

- hold_status is always "HOLD" (release requires explicit human authorization)
- All fields are immutable (frozen dataclass)
- No I/O, no network, no random, no timestamps

## Renderer Functions

- `render_release_hold_dashboard_md` — full dashboard markdown with all sections
- `render_hold_status_md` — single-line hold status display

## Current State

- 9 HIGH-risk files frozen
- 22 MEDIUM-risk files governed
- 6 governance layers active (read-only hook, freeze-aware, untracked-freeze, frozen-backlog, medium-operational, human-approval)
- Release hold: HOLD
