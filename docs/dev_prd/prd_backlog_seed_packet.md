# PRD Backlog Seed Packet — T880

## Purpose

Deterministic seed packet for future 500+ task backlog. Establishes milestones, task ranges, frozen boundaries, and human review gates.

## Component

- **Module:** `core/prd_backlog_seed_packet.py`
- **Dataclass:** `PrdBacklogSeedPacket` (frozen=True)
- **Functions:**
  - `build_prd_backlog_seed_packet(target_task_count=500)`
  - `backlog_seed_packet_to_dict(packet)`
  - `backlog_seed_packet_to_markdown(packet)`

## Fields

| Field | Type | Description |
|-------|------|-------------|
| backlog_id | str | Unique seed identifier |
| target_task_count | int | Minimum 500 |
| proposed_milestones | List[str] | M1-M8 milestone definitions |
| proposed_task_ranges | List[str] | T881+ range assignments |
| frozen_ranges | List[str] | Ranges that cannot execute (M8) |
| next_safe_range | str | Must contain HUMAN_REVIEW_REQUIRED |
| notes | List[str] | Safety and context notes |

## Milestones

- M1: PRD automation control plane
- M2: 500-task planning layer
- M3: read-only hook prototype design
- M4: offline evidence writer design
- M5: manual review CLI design
- M6: read-only hook implementation review
- M7: runtime integration review
- M8: live execution frozen

## Safety Rules

- `target_task_count` must be >= 500
- M8 live execution is frozen — no authorization for live trading
- `next_safe_range` requires HUMAN_REVIEW_REQUIRED marker
- No authorization for live trading

## Tests

```bash
python3 -m pytest tests/unit/test_prd_backlog_seed_packet.py -v
```

## T880 Acceptance

- [x] frozen dataclass
- [x] target_task_count >= 500 enforced
- [x] M8 frozen
- [x] next_safe_range HUMAN_REVIEW_REQUIRED
- [x] deterministic output
- [x] dict and markdown serializers
