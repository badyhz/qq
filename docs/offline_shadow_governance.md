# Offline Shadow Research Governance

## Safety Policy Enforcement

The offline shadow research pipeline enforces a strict safety policy at
every layer:

### Hard Constraints

| Constraint | Enforced By | Behavior |
|-----------|-------------|----------|
| `release_hold == "HOLD"` | `OfflineShadowSafetyPolicy.__post_init__` | Raises `ValueError` on construction |
| `no_live == True` | Data model + pipeline checks | No live execution code path exists |
| `no_submit == True` | Data model + pipeline checks | No order submission code path exists |
| `no_exchange == True` | Data model + pipeline checks | No exchange connectivity code path exists |
| No I/O in core/ | Code review + import analysis | Core modules are pure functions only |
| Frozen dataclasses | `@dataclass(frozen=True)` | Runtime `AttributeError` on mutation |

### Enforcement Points

1. **Construction time** -- Safety policy validates `release_hold` in
   `__post_init__`. Invalid values are rejected immediately.

2. **Plan creation** -- Every experiment plan embeds a safety policy.
   Plans with invalid policies cannot be constructed.

3. **Pipeline execution** -- The pipeline orchestrator checks safety
   flags before processing each experiment.

4. **Bundle output** -- The bundle manifest includes safety policy
   metadata for audit purposes.

## Release Hold Mechanism

The `release_hold` field is the master kill switch for the entire
offline shadow research system.

```
release_hold = "HOLD"   --> Pipeline operates normally
release_hold = "RELEASE" --> ValueError (blocked at construction)
release_hold = ""        --> ValueError (blocked at construction)
release_hold = None      --> TypeError (blocked at construction)
```

The only valid value is `"HOLD"`. This is intentional -- the shadow
pipeline is designed to never release experiments to production. Any
deployment decision must go through a separate, explicit approval
process outside this pipeline.

### Rationale

By making "HOLD" the only valid value, we eliminate the class of bugs
where a misconfigured safety policy accidentally permits live execution.
The pipeline is physically incapable of releasing anything.

## Audit Trail Requirements

Every pipeline run produces an audit trail consisting of:

1. **Experiment plan** -- Full specification of all experiments, symbols,
   timeframes, windows, and parameter sets.

2. **Run config** -- Configuration snapshot including fixture and output
   directories.

3. **Safety policy** -- Embedded in every experiment and the plan itself.

4. **Metric results** -- Computed metrics for each experiment run.

5. **Scorecard grades** -- Quality assessments for each experiment.

6. **Recommendations** -- DEPLOY/WATCH/REJECT decisions with rationale
   and risk factors.

7. **Bundle manifest** -- SHA256 hashes of all artifacts in the output
   bundle.

All artifacts are written to the output directory and included in the
bundle. The manifest enables integrity verification.

## Review Board Integration

The recommendation engine produces structured output suitable for
review board consumption:

```
Recommendation(
    experiment_id="exp_001",
    action="DEPLOY",
    confidence=0.75,
    rationale="Positive expectancy with adequate sample quality.",
    risk_factors=("win_rate=0.58 below 60%",),
    next_steps=("Proceed to paper trading validation.",),
)
```

Review boards should:
1. Examine all DEPLOY recommendations before any production action
2. Verify confidence scores against independent analysis
3. Check risk factors for acceptable risk tolerance
4. Confirm next steps are actionable and scheduled

## Frozen File Protection

The following files in `core/` are frozen and must never be modified:

- `data_feed.py`, `signal_engine.py`, `risk_manager.py`
- `execution.py`, `order_manager.py`, `trade_logger.py`
- All other files listed in the project's frozen boundary

### Protection Mechanisms

1. **Git pre-commit hooks** -- Verify frozen files are not staged
2. **CI checks** -- Automated verification that frozen files are unchanged
3. **Code review** -- Manual review of any changes near frozen boundaries

### Consequences of Violation

Modifying a frozen file:
- May break production trading logic
- May introduce security vulnerabilities
- Will be rejected by CI
- Requires explicit board approval to proceed

## Offline Shadow vs Live Pipeline

| Aspect | Offline Shadow | Live Pipeline |
|--------|---------------|---------------|
| Data source | Historical fixtures | Real-time market data |
| Execution | Simulated (dry-run) | Real orders |
| Exchange | None (no_exchange=True) | Binance API |
| Safety | release_hold="HOLD" | Separate approval gate |
| Output | Reports + recommendations | Trade logs + P&L |
| Network | Zero network calls | Full exchange connectivity |

The shadow pipeline is completely isolated from live systems. It shares
no state, no network connections, and no execution paths with the live
trading system.
