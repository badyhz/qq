# T1061-T1160 Dirty Workspace Packet

## Status

- Classification: COMPLETE
- HIGH-risk files: 9 frozen
- Governance policies: DEFINED

## Frozen HIGH-Risk Files

| File | Risk | Reason |
|------|------|--------|
| main.py | HIGH | Entry point |
| core/execution.py | HIGH | Order execution |
| core/order_manager.py | HIGH | Order tracking |
| core/data_feed.py | HIGH | Market data |
| core/live_runner.py | HIGH | Live runner |
| core/single_call_recorder.py | HIGH | Call recording |
| core/evidence_recorder.py | HIGH | Evidence recording |
| utils/evidence_recorder.py | HIGH | Evidence utility |
| config.yaml | HIGH | Configuration |

## Classification Complete

- HIGH: 9 files -- frozen, no modification allowed
- MEDIUM: governance model files -- modifiable within task scope
- LOW: documentation, tests -- modifiable

## Governance Policies Defined

1. dirty_workspace_high_risk_policy.md -- freeze enforcement
2. dirty_workspace_medium_risk_policy.md -- scoped modification
3. dirty_workspace_low_risk_policy.md -- free modification
4. dirty_workspace_tracked_file_policy.md -- git tracking rules
5. dirty_workspace_untracked_file_policy.md -- untracked file handling
6. dirty_workspace_duplicate_file_policy.md -- duplicate detection
7. dirty_workspace_commit_isolation_policy.md -- commit separation

## Conclusion

Workspace classification is stable. HIGH-risk files are frozen. Governance policies cover all file categories. No violations detected in T1061-T1160 scope.
