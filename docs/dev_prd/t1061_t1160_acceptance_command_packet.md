# T1061-T1160 Acceptance Command Packet

## Pytest Commands by Test Group

### Freeze-Aware Queue Tests

```bash
python3 -m pytest tests/unit/test_freeze_aware_task_queue_overview.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_admission_rules.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_denial_rules.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_dependency_rules.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_blocked_state.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_pass_state.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_partial_state.py -v
python3 -m pytest tests/unit/test_freeze_aware_task_review_required_state.py -v
```

### Dirty Workspace Tests

```bash
python3 -m pytest tests/unit/test_dirty_workspace_governance_overview.py -v
python3 -m pytest tests/unit/test_dirty_workspace_high_risk_policy.py -v
python3 -m pytest tests/unit/test_dirty_workspace_medium_risk_policy.py -v
python3 -m pytest tests/unit/test_dirty_workspace_low_risk_policy.py -v
python3 -m pytest tests/unit/test_dirty_workspace_tracked_file_policy.py -v
python3 -m pytest tests/unit/test_dirty_workspace_untracked_file_policy.py -v
python3 -m pytest tests/unit/test_dirty_workspace_duplicate_file_policy.py -v
```

### Human Review Gate Tests

```bash
python3 -m pytest tests/unit/test_human_review_gate_overview.py -v
python3 -m pytest tests/unit/test_human_review_gate_decision_taxonomy.py -v
python3 -m pytest tests/unit/test_human_review_gate_approval_states.py -v
python3 -m pytest tests/unit/test_human_review_gate_rejection_states.py -v
python3 -m pytest tests/unit/test_human_review_gate_escalation_rules.py -v
```

### Full Range

```bash
python3 -m pytest tests/unit/ -k "freeze_aware or dirty_workspace or human_review_gate" -v
```

## Import Verification Commands

```bash
python3 -c "import core.freeze_aware_task_queue_overview"
python3 -c "import core.freeze_aware_task_admission_rules"
python3 -c "import core.freeze_aware_task_denial_rules"
python3 -c "import core.dirty_workspace_governance_overview"
python3 -c "import core.dirty_workspace_high_risk_policy"
python3 -c "import core.human_review_gate_overview"
python3 -c "import core.human_review_gate_decision_taxonomy"
```

## Expected Results

- All pytest commands: 0 failures, 0 errors
- All import commands: exit code 0, no ImportError
- Total test count: approximately 20 test files passing
