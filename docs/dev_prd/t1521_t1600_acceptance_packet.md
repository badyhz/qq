# T1521-T1600 Acceptance Command Packet

## Pytest Commands by Test Group

### Compatibility Tests

```bash
python3 -m pytest tests/unit/test_t1561_t1600_compatibility.py -v
```

### Existing Governance Tests (must still pass)

```bash
python3 -m pytest tests/unit/test_read_only_hook_* -q
python3 -m pytest tests/unit/test_prd_* -q
python3 -m pytest tests/unit/test_dev_prd_control_plane.py -q
```

### Full Acceptance Suite

```bash
python3 -m pytest tests/unit/test_t1561_t1600_compatibility.py -v --tb=short
```

## Doc Verification Commands

```bash
# Verify all new docs exist
test -f docs/dev_prd/frozen_backlog_review_report_cli.md
test -f docs/dev_prd/frozen_backlog_review_report_materializer.md
test -f docs/dev_prd/t1521_t1600_acceptance_packet.md
test -f docs/dev_prd/t1521_t1600_safety_boundary_packet.md
test -f docs/dev_prd/t1521_t1600_final_closeout_report.md

# Verify updated docs contain T1521-T1600 references
grep -q "T1521" docs/dev_prd/runtime_governance_task_queue.md
grep -q "T1600" docs/dev_prd/runtime_governance_task_queue.md
grep -q "T1521" docs/dev_prd/runtime_governance_current_state.md
```

## Expected Results

- All pytest runs: PASSED
- All doc files: exist
- All grep checks: exit code 0
