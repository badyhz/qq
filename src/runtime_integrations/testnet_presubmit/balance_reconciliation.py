"""Balance reconciliation types."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class BalanceSnapshot:
    asset: str
    free: float
    locked: float
    total: float
    simulated: bool
    def to_dict(self) -> dict:
        return {"asset": self.asset, "free": self.free, "locked": self.locked, "total": self.total, "simulated": self.simulated}

@dataclass(frozen=True)
class BalanceReconResult:
    asset: str
    status: str  # MATCH, WARN, BLOCKED
    checks: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"asset": self.asset, "status": self.status, "checks": list(self.checks)}

def reconcile_balance(expected: BalanceSnapshot, reported: BalanceSnapshot | None) -> BalanceReconResult:
    checks = []
    if reported is None:
        return BalanceReconResult(expected.asset, "BLOCKED", ("MISSING_ASSET",))
    if expected.free != reported.free:
        checks.append(f"FREE_MISMATCH: expected={expected.free}, reported={reported.free}")
    else:
        checks.append("free_match")
    if expected.total != reported.total:
        checks.append(f"TOTAL_MISMATCH: expected={expected.total}, reported={reported.total}")
    else:
        checks.append("total_match")
    if reported.total < 0:
        checks.append("NEGATIVE_BALANCE")
    status = "MATCH" if not any("MISMATCH" in c or "NEGATIVE" in c for c in checks) else "BLOCKED"
    return BalanceReconResult(expected.asset, status, tuple(checks))

def write_results(results: list[BalanceReconResult], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
