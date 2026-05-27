# PRD Queue Closeout Packet — T871

## Purpose

Generates a frozen closeout packet for a completed PRD task queue range.

## Artifact

- `core/prd_queue_closeout_packet.py` — dataclass + builder + serializers
- `tests/unit/test_prd_queue_closeout_packet.py` — unit tests

## Dataclass: PrdQueueCloseoutPacket

| Field | Type | Default |
|---|---|---|
| queue_range | str | "T865-T872" |
| completed_tasks | List[str] | T865-T872 |
| expected_artifacts | int | 8 |
| validation_verdict | str | "PASS" |
| safety_verdict | str | "PASS" |
| final_status | str | "COMPLETED" |
| hard_stop_task | str | "T872" |
| next_task_allowed | bool | False |
| notes | List[str] | default notes |

## Functions

- `build_prd_queue_closeout_packet(...)` — construct with defaults
- `queue_closeout_packet_to_dict(packet)` — serialize to dict
- `queue_closeout_packet_to_markdown(packet)` — render as markdown

## Safety

- `next_task_allowed` defaults to False
- Hard stop at T872 — no next task without human instruction
