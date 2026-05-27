# T1167 - Untracked Freeze Ledger: Human Review Workflow

## Workflow Steps

### Step 1: Classify

- Scan untracked files via `git status`.
- For each file, create a ledger entry with state=NEW.
- Compute content hash (SHA-256).
- Scan for references (imports, configs, module loads).
- Assign initial state based on scan results.

**Output:** Ledger entry with state, hash, reference count.

### Step 2: Assess Risk

- Apply risk taxonomy rules to each classified file.
- Assign risk class: HIGH, MEDIUM, or LOW.
- Record risk assessment in ledger entry.

**Output:** Ledger entry with risk_class field populated.

### Step 3: Request Review

- Generate a review report listing all unclassified or unreviewed files.
- Group by risk class (HIGH first, then MEDIUM, then LOW).
- Present to human operator with recommended actions.

**Output:** Review report for human consumption.

### Step 4: Approve or Reject

- Human operator reviews each file and decides:
  - APPROVE: File may proceed to its recommended action.
  - REJECT: File remains in current state; reason recorded.
  - DEFER: File remains in current state; re-review scheduled.
- Decision recorded in ledger with operator identity and reason.

**Output:** Ledger entry with human_approval field and decision record.

### Step 5: Log Decision

- Append decision to ledger as an immutable record.
- If approved, execute the permitted action (e.g., unfreeze, quarantine).
- If rejected, file remains frozen; no action taken.
- Generate summary report of all decisions.

**Output:** Updated ledger, summary report.

## Escalation Rules

| Condition                          | Action                              |
|------------------------------------|-------------------------------------|
| HIGH risk file, no review in 7d   | Alert operator, escalate priority   |
| Any file in QUARANTINE > 30d      | Alert operator, recommend deletion  |
| Duplicate detected                 | Immediate notification              |
