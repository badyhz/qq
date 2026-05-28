# Corrupted JSON Recovery

## Symptoms
- `json.JSONDecodeError` when reading artifact
- Empty JSON file (0 bytes)
- Truncated JSON file
- `python3 -m json.tool` fails on artifact

## Likely Causes
- Process interrupted during write
- Disk space exhaustion
- Concurrent write conflict
- Filesystem error

## Commands to Inspect
```bash
# Check file size
ls -la /tmp/multi_strategy_research_quality_gate/*.json

# Try to parse
python3 -m json.tool /tmp/multi_strategy_research_quality_gate/manifest.json 2>&1

# Check for empty files
find /tmp/ -name "*.json" -size 0

# Check disk space
df -h /tmp
```

## Safe Recovery Commands
```bash
# Delete corrupted file
rm /tmp/multi_strategy_research_quality_gate/manifest.json

# Re-generate by re-running the stage
python3 scripts/run_multi_strategy_research_quality_gate.py \
  --input-dir /tmp/multi_strategy_research_workbench \
  --output-dir /tmp/multi_strategy_research_quality_gate \
  --deterministic-seed 424242 --strict --release-hold HOLD

# Verify JSON is valid
python3 -m json.tool /tmp/multi_strategy_research_quality_gate/manifest.json
```

## Forbidden Recovery Commands
- Do not manually edit JSON files
- Do not merge partial JSON
- Do not use corrupted data
- Do not skip validation

## Escalation Rule
If corruption persists:
1. Check disk health
2. Check filesystem
3. Try different output directory
4. Run full test suite to verify code integrity

## Final Verification
```bash
# Verify all JSON files are valid
find /tmp/multi_strategy_research_quality_gate/ -name "*.json" -exec python3 -m json.tool {} \; > /dev/null && echo "ALL JSON VALID" || echo "CORRUPTION DETECTED"
```

## Safety
release_hold = HOLD. Advisory only. Human review required.
