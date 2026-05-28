# Missing Quality Artifacts Recovery

## Symptoms
- Quality gate output directory missing or empty
- `quality_gate.json` not found
- `manifest.json` not found
- Downstage stages fail with "input not found"

## Likely Causes
- Quality gate stage was skipped
- Quality gate stage failed silently
- Output directory was cleaned
- Disk space issue during write

## Commands to Inspect
```bash
# Check if output directory exists
ls -la /tmp/multi_strategy_research_quality_gate/

# Check if workbench input exists
ls -la /tmp/multi_strategy_research_workbench/

# Check disk space
df -h /tmp

# Check for partial writes
find /tmp/multi_strategy_research_quality_gate/ -name "*.json" -size 0
```

## Safe Recovery Commands
```bash
# Re-run quality gate
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 --strict --release-hold HOLD

# Verify output
ls -la /tmp/multi_strategy_research_quality_gate/
python3 -m json.tool /tmp/multi_strategy_research_quality_gate/manifest.json
```

## Forbidden Recovery Commands
- Do not create fake/artificial quality gate outputs
- Do not copy outputs from a different run
- Do not skip quality gate and proceed to next stage
- Do not change release-hold from HOLD

## Escalation Rule
If quality gate fails repeatedly:
1. Check workbench output integrity
2. Check fixture data integrity
3. Run full test suite: `PYTHONPATH=. .venv/bin/pytest -q`
4. If tests fail, see `docs/recovery/failed_full_suite_recovery.md`

## Final Verification
```bash
# Verify quality gate output
python3 -c "
import json
m = json.load(open('/tmp/multi_strategy_research_quality_gate/manifest.json'))
assert m['release_hold'] == 'HOLD'
assert m['advisory_only'] == True
print('PASS: Quality gate output valid')
"
```

## Safety
release_hold = HOLD. Advisory only. Human review required.
