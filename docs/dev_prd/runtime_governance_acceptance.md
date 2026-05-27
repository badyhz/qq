# Runtime Governance Acceptance Rules

## Universal Acceptance

Every task must satisfy:

- unit tests pass
- deterministic markdown output
- dict serializers stable
- no forbidden files modified
- git status reviewed
- commits grouped by task

## Required Verification Commands

```bash
python3 -m pytest tests/unit/test_runtime_governance_readonly_* -q
python3 -m pytest tests/unit/test_runtime_governance_* -q
python3 -m pytest tests/unit/test_governance_failure_* -q
python3 -m pytest tests/unit/test_order_manager.py -q
```

## PRD Control-Plane Acceptance

- docs/dev_prd files exist
- required headings exist
- forbidden terms appear in safety boundaries
- task queue lists completed and future tasks
- agent protocol includes output format and stop conditions

## Result Definitions

- **PASS**: all tests pass, all files committed, no violations
- **PARTIAL**: some tests pass, some commits succeeded, blockers documented
- **FAIL**: tests failed, commits failed, violations detected
- **BLOCKED**: cannot proceed due to frozen boundary or permission issue

## Never Claim PASS If

- tests were denied and not manually verified
- commit failed
- unauthorized files modified
- downstream task required changing frozen API
