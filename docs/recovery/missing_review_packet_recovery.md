# Missing Review Packet Recovery

## Symptoms
- Review packet directory missing or empty
- `review_packet.json` not found
- Review validation fails
- Human review cannot proceed

## Likely Causes
- Review packet build was skipped
- Build failed silently
- Input data missing (quality gate, browser, comparison)
- Output directory cleaned

## Commands to Inspect
```bash
# Check review packet directory
ls -la /tmp/research_human_review_packet/

# Check inputs exist
ls -la /tmp/multi_strategy_research_quality_gate/
ls -la /tmp/research_artifact_browser/
ls -la /tmp/research_comparison_analytics/

# Check for errors in build log
# (if captured)
```

## Safe Recovery Commands
```bash
# Verify all inputs exist
for dir in /tmp/multi_strategy_research_quality_gate /tmp/research_artifact_browser /tmp/research_comparison_analytics; do
  test -d "$dir" && echo "OK: $dir" || echo "MISSING: $dir"
done

# Re-build review packet
python3 scripts/build_research_human_review_packet.py \
  --quality-dir /tmp/multi_strategy_research_quality_gate \
  --artifact-browser-dir /tmp/research_artifact_browser \
  --comparison-dir /tmp/research_comparison_analytics \
  --output-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD

# Validate
python3 scripts/validate_research_human_review_packet.py \
  --review-dir /tmp/research_human_review_packet \
  --strict --release-hold HOLD
```

## Forbidden Recovery Commands
- Do not create fake review packets
- Do not skip review packet validation
- Do not use incomplete inputs
- Do not change release-hold

## Escalation Rule
If review packet cannot be built:
1. Check all upstream outputs exist
2. Re-run upstream stages if needed
3. Run full test suite
4. If still failing, escalate to human operator

## Final Verification
```bash
# Verify review packet
python3 -c "
import json
rp = json.load(open('/tmp/research_human_review_packet/review_packet.json'))
assert rp['release_hold'] == 'HOLD'
assert rp['advisory_only'] == True
print('PASS: Review packet valid')
"
```

## Safety
release_hold = HOLD. Advisory only. Human review required.
