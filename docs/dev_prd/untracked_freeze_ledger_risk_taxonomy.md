# T1163 - Untracked Freeze Ledger: Risk Taxonomy

## Risk Classes

### HIGH

**Criteria:**
- File could directly affect trading logic, order execution, or risk management.
- File contains or references secrets, API keys, or credentials.
- File is a runtime entry point or planner module.
- File modifies system behavior if imported or executed.

**Examples:**
- Untracked Python module with trade execution logic.
- Untracked config file containing API keys.
- Untracked shell script that starts a live process.

**Default action:** BLOCK. No automated action permitted. Requires human review
with explicit approval before any state transition beyond FROZEN.

---

### MEDIUM

**Criteria:**
- File is infrastructure, CI/CD, or configuration with indirect system impact.
- File is a test helper or fixture that could affect test outcomes.
- File is a documentation file that contains operational instructions.

**Examples:**
- Untracked Makefile or Dockerfile.
- Untracked test fixture with mock data.
- Untracked runbook with deployment steps.

**Default action:** HOLD. Automated logging and reporting permitted. No
auto-commit, auto-wire, or auto-run. Human review recommended before integration.

---

### LOW

**Criteria:**
- File is documentation, notes, or reference material with no execution path.
- File is a test output, log dump, or temporary artifact.
- File has no imports, no references, and no configuration entry.

**Examples:**
- Untracked markdown design doc.
- Untracked `.txt` notes file.
- Untracked test output CSV.

**Default action:** LOG. Automated logging and reporting permitted. Human review
optional but recommended before cleanup.
