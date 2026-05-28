# Invalid Safety Flags Recovery

## Symptoms
- Governance validation fails on safety flags
- Experiment validation fails on safety flags
- Manifest shows non-HOLD release_hold
- Advisory only = false
- Human review required = false

## Likely Causes
- Incorrect experiment definition
- Manual edit introduced error
- Template mismatch
- Copy-paste error

## Commands to Inspect
```bash
# Check experiment catalog
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/safety_check \
  --strict --release-hold HOLD

# Check specific experiment
python3 -c "
import json
catalog = json.load(open('tests/fixtures/offline_research_experiment_library/experiment_catalog.json'))
for exp in catalog['experiments']:
    sf = exp.get('safety_flags', {})
    if sf.get('release_hold') != 'HOLD':
        print(f'INVALID: {exp[\"experiment_id\"]} release_hold={sf.get(\"release_hold\")}')
    if sf.get('advisory_only') != True:
        print(f'INVALID: {exp[\"experiment_id\"]} advisory_only={sf.get(\"advisory_only\")}')
    if sf.get('human_review_required') != True:
        print(f'INVALID: {exp[\"experiment_id\"]} human_review_required={sf.get(\"human_review_required\")}')
print('Check complete')
"

# Check governance
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/governance_check \
  --strict --release-hold HOLD
```

## Safe Recovery Commands
```bash
# Fix experiment definition
# Edit the invalid experiment in experiment_catalog.json
# Ensure safety_flags contains:
#   "release_hold": "HOLD"
#   "advisory_only": true
#   "human_review_required": true
#   "no_live": true
#   "no_submit": true
#   "no_exchange": true
#   "no_network": true
#   "no_runtime_integration": true
#   "no_planner_integration": true

# Re-validate
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/safety_check_after \
  --strict --release-hold HOLD
```

## Forbidden Recovery Commands
- Do not change release_hold from HOLD
- Do not set advisory_only to false
- Do not set human_review_required to false
- Do not skip validation

## Escalation Rule
If safety flags cannot be fixed:
1. Do not proceed
2. Do not run pipeline
3. Escalate to human operator
4. Safety boundary violation is critical

## Final Verification
```bash
# All safety checks must pass
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/safety_final \
  --strict --release-hold HOLD && echo "PASS" || echo "FAIL"
```

## Safety
release_hold = HOLD. Advisory only. Human review required. Any safety flag violation is critical.
