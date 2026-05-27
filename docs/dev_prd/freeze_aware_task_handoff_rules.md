# T1085 - Freeze-Aware Task Handoff Rules

## Purpose

Define requirements for transferring task ownership between agents.

## Handoff Requirements

### 1. Explicit File List

Every handoff packet MUST include the complete list of files the receiving
agent is expected to touch. No implicit file inheritance from the sending
agent.

### 2. No Implicit State Transfer

The sending agent MUST NOT assume the receiving agent has any context
beyond what is in the handoff packet. All relevant state MUST be
serialized in the packet.

### 3. Verification Command Per Handoff

Every handoff packet MUST include a verification command that the
receiving agent can run to confirm the handoff is valid. Example:
`python3 -m pytest tests/unit/test_<task>.py`

## Handoff Packet Structure

```
HandoffPacket(
    from_agent=<sender_id>,
    to_agent=<receiver_id>,
    task_id=<task>,
    explicit_files=(<file_list>),
    verification_command=<cmd>,
    notes=<optional>,
)
```

## Validation

On receipt, the queue verifies:

1. `from_agent` is the current owner of the task.
2. `to_agent` is a valid agent in the registry.
3. `explicit_files` does not overlap frozen files.
4. `verification_command` is non-empty.

## Safety Statement

Handoff is a coordination event. No files are moved or modified by the
queue itself.
