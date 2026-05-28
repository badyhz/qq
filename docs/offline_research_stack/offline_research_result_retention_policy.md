# Offline Research Result Retention Policy

## Policy

Research artifacts are retained based on their type, source phase, and audit value.

## Retention Rules

### KEEP_LATEST
- JSON and markdown artifacts from workbench phases
- Only latest version kept
- Older versions may be pruned

### KEEP_TAGGED
- Artifacts from quality gate and governance phases
- Tagged versions preserved
- Used for regression comparison

### KEEP_FOR_AUDIT
- Manifest files
- Frozen inventory artifacts
- Decision matrix artifacts
- Archive plan artifacts
- Never pruned without human approval

### TEMP_REGENERABLE
- Log files
- Plain text output
- Can be regenerated from source
- May be pruned after audit window

### REVIEW_REQUIRED
- Artifacts that don't fit other categories
- Must be reviewed before retention decision
- Cannot be pruned until reviewed

## Pruning Rules

1. TEMP_REGENERABLE: Prune after 30 days
2. KEEP_LATEST: Prune older versions after 90 days
3. KEEP_TAGGED: Never auto-prune
4. KEEP_FOR_AUDIT: Never auto-prune
5. REVIEW_REQUIRED: Never prune until reviewed

## Safety Boundary

- No auto-deletion of KEEP_FOR_AUDIT
- No auto-deletion of KEEP_TAGGED
- release_hold = HOLD
- Advisory only
