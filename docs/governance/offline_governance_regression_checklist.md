# Offline Governance Regression Checklist

## Pre-flight

- [ ] release_hold = HOLD
- [ ] No network connectivity required
- [ ] No frozen files to be executed
- [ ] No live/testnet/runtime activation

## Checks

- [ ] Experiment library tests pass
- [ ] Documentation governance tests pass
- [ ] Frozen inventory report builds
- [ ] Decision matrix builds
- [ ] Archive plan builds
- [ ] Result catalog builds

## Post-flight

- [ ] All checks PASS
- [ ] No forbidden commands used
- [ ] No shell=True in any subprocess
- [ ] Safety boundary documented in all outputs
- [ ] release_hold remains HOLD

## Failure Response

1. Identify failed check
2. Review error output
3. Fix underlying issue
4. Re-run regression pack
5. Verify all checks pass
