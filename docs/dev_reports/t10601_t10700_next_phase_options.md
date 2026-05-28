# T10601-T10700 Next Phase Options

## 1. What Not To Do Next

- Do NOT activate live trading
- Do NOT activate testnet submission
- Do NOT modify release_hold
- Do NOT modify safety flags
- Do NOT touch untracked live/testnet/shadow files
- Do NOT add exchange integration
- Do NOT add runtime integration
- Do NOT add network access
- Do NOT add auto-promotion

## 2. Safe Next Options

| Option | Range | Description |
|--------|-------|-------------|
| A | T10701-T11000 | Documentation Consolidation / Operator Manual |
| B | T10701-T11200 | Offline Research Experiment Library |
| C | T10701-T10900 | More Fixture/Test Debt |
| D | T10701-T10900 | Offline Report UX Polish |

## 3. Recommended Option A — Documentation Consolidation

**Range:** T10701-T11000

**Goal:** Consolidate the 8+ dev_reports and scattered docs into a single operator manual for the offline research stack.

**Scope:**
- Create `docs/operator_manual_offline_research.md`
- Consolidate all phase closeout reports into a unified reference
- Document all CLI commands with examples
- Document the full pipeline from data to review
- Document safety boundary and release criteria
- Document fixture management
- Document test re-run procedures

**Benefits:**
- Single source of truth for operators
- Reduces onboarding friction
- No code changes, pure documentation
- Zero risk

**Deliverables:**
- `docs/operator_manual_offline_research.md`
- Updated dev_reports index
- No code changes

## 4. Recommended Option B — Offline Research Experiment Library

**Range:** T10701-T11200

**Goal:** Build a curated library of ready-to-run offline research experiments.

**Scope:**
- Define experiment schema (config + fixtures + expected outputs)
- Create 5-10 sample experiments covering different research scenarios
- CLI to list, run, and validate experiments
- Integration with existing comparison/report/review workflow
- Test coverage for experiment runner
- Experiment result archival

**Benefits:**
- Makes the research stack immediately usable
- Provides templates for new experiments
- Validates the full pipeline end-to-end
- Stays within offline/advisory boundary

**Deliverables:**
- `core/experiment_library.py`
- `tests/unit/test_experiment_library_*.py`
- `experiments/` directory with sample configs
- CLI entry points for experiment management

## 5. Recommended Option C — More Fixture/Test Debt

**Range:** T10701-T10900

**Goal:** Address the 6 skipped tests and expand fixture coverage.

**Scope:**
- Investigate and resolve 6 skipped tests
- Add more research_quality fixtures if gaps exist
- Add edge case tests for comparison/report/review workflows
- Improve test isolation and speed

**Benefits:**
- Higher test confidence
- Cleaner test output
- Addresses known debt

## 6. Recommended Option D — Offline Report UX Polish

**Range:** T10701-T10900

**Goal:** Improve the usability of offline reports and browser.

**Scope:**
- Improve report rendering quality
- Add filtering/sorting to artifact browser
- Improve comparison report layout
- Add summary statistics to reports
- Better error messages in CLIs

**Benefits:**
- Better operator experience
- More useful reports
- Stays within offline boundary

## 7. Parked Option — Testnet/Runtime Review, Still Frozen

Testnet and runtime integration remain frozen pending:
1. release_hold lift
2. Explicit human approval
3. Safety boundary review
4. Risk assessment

Do not start testnet/runtime work until these conditions are met.

## 8. Forbidden Next Actions

| Action | Status |
|--------|--------|
| Live trading | FORBIDDEN |
| Testnet submission | FORBIDDEN |
| Exchange integration | FORBIDDEN |
| Runtime integration | FORBIDDEN |
| Auto-promotion | FORBIDDEN |
| Network access | FORBIDDEN |
| release_hold modification | FORBIDDEN |
| Safety flag modification | FORBIDDEN |
| Touching untracked files | FORBIDDEN |

## 9. Agent Prompt Template For Next Phase

```
Task: T[next_start]-T[next_end] [Phase Name]

Context:
- Offline research stack complete through T10600
- Full suite: 7248 passed, 6 skipped, 0 failed
- release_hold: HOLD
- Safety boundary: offline/advisory/human_review_required

Rules:
- No live/testnet/runtime activation
- No safety flag changes
- No touching untracked external files
- All new code must be testable offline
- All tests must pass before commit

Scope:
[specific scope here]
```

## 10. Final Recommendation

**T10701-T11000 Documentation Consolidation / Operator Manual** is the recommended next phase.

Reasons:
1. Lowest risk — documentation only
2. Highest immediate value — single reference for the stack
3. Prerequisite for any future phase — operator manual needed before experiment library
4. No code changes — zero chance of breaking existing tests
5. Completes the closeout cycle — proper documentation for a complete stack

Alternative: **T10701-T11200 Offline Research Experiment Library** if the operator manual is deprioritized in favor of making the stack immediately usable.

Do NOT recommend live/testnet/runtime activation. The offline stack must be fully documented and validated before any live boundary discussion.
