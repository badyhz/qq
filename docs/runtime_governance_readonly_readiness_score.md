# T836 — Runtime Governance Read-Only Readiness Score

Pure, deterministic readiness score for the read-only governance layer.

## Dataclass

`RuntimeGovernanceReadOnlyReadinessScore` (frozen=True):
- `score: int` — computed score (0-100)
- `max_score: int` — always 100
- `percent: float` — score/max_score * 100
- `grade: str` — A/B/C/D/F
- `blockers: List[str]` — critical failures
- `warnings: List[str]` — non-critical issues
- `notes: List[str]` — metadata

## Scoring

Start at 100:
- Each scenario fail: -20
- Side-effect verdict != PASS: -25
- Manifest verdict != PASS: -20
- Final verdict != PASS: grade capped at F

## Grade Thresholds

- A >= 90
- B >= 75
- C >= 60
- D >= 40
- F < 40

## Functions

- `compute_readonly_readiness_score(packet) -> RuntimeGovernanceReadOnlyReadinessScore`
- `readonly_readiness_score_to_dict(score) -> Dict`
- `readonly_readiness_score_to_markdown(score) -> str`

## Properties

- Pure, deterministic
- No I/O, no timestamps, no random
- Perfect packet produces score=100, grade="A"
