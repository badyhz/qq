"""Exchange harness result types."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class HarnessStep:
    step: str
    status: str  # PASS, SIMULATED, BLOCKED
    detail: str
    def to_dict(self) -> dict:
        return {"step": self.step, "status": self.status, "detail": self.detail}

@dataclass(frozen=True)
class HarnessResult:
    steps: tuple[HarnessStep, ...]
    no_network: bool
    no_real_key: bool
    no_submit: bool
    overall: str
    def to_dict(self) -> dict:
        return {"steps": [s.to_dict() for s in self.steps], "no_network": self.no_network, "no_real_key": self.no_real_key, "no_submit": self.no_submit, "overall": self.overall}
