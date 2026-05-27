# Human Review Gate Escalation Rules

## Escalation Levels

### L1_AGENT

**Role:** Automated agent (Claude Code or similar).

**Authority:** May propose actions. May NOT approve any gate. May only escalate to L2.

**Required evidence at this level:**
- Action description
- Affected files/modules
- Risk assessment (dry-run only)

### L2_OPERATOR

**Role:** Human operator (project owner / developer).

**Authority:** May approve low-risk gates. May escalate to L3.

**Required evidence at this level:**
- All L1 evidence
- Test results (pass/fail)
- Dry-run verification output
- Risk impact statement

### L3_ADMIN

**Role:** Human administrator with full system access.

**Authority:** May approve medium-risk gates. May approve permanent rejections override. May escalate to L4.

**Required evidence at this level:**
- All L2 evidence
- Safety verification checklist completed
- Rollback plan documented
- Diff review of all affected files

### L4_EMERGENCY

**Role:** Emergency authority. Highest escalation tier.

**Authority:** May approve any gate including high-risk. May override permanent rejections. May authorize emergency actions.

**Required evidence at this level:**
- All L3 evidence
- Emergency justification documented
- Post-incident review plan
- Full system state snapshot

## Escalation Triggers

| Trigger | From Level | To Level |
|---------|-----------|----------|
| Gate exceeds current authority | L1 | L2 |
| Risk level is HIGH or CRITICAL | L2 | L3 |
| Frozen file modification required | L2 | L3 |
| Live trading action proposed | L3 | L4 |
| Credential access required | L2 | L3 |
| Exchange connection required | L2 | L3 |
| Planner integration change | L2 | L3 |
| Emergency override needed | Any | L4 |

## Escalation Protocol

1. Current level documents reason for escalation.
2. All accumulated evidence carries forward to next level.
3. Higher level may approve, reject, or escalate further.
4. No level may be skipped without documented justification.
5. All escalation decisions are recorded in gate history.
