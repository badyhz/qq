"""Systemd template validator. Validates service templates without installing."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class TemplateValidation:
    file: str
    valid: bool
    checks: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"file": self.file, "valid": self.valid, "checks": list(self.checks)}

FORBIDDEN_IN_TEMPLATES = ("systemctl enable", "systemctl start", "api_key=", "secret=", "webhook_url=", "REAL_TRADING", "LIVE_TRADING")
REQUIRED_IN_TEMPLATES = ("DRY_RUN", "NO_SUBMIT")

def validate_template(path: pathlib.Path) -> TemplateValidation:
    if not path.exists():
        return TemplateValidation(path.name, False, ("file_missing",))
    content = path.read_text(encoding="utf-8")
    checks = []
    ok = True
    for f in FORBIDDEN_IN_TEMPLATES:
        if f in content:
            checks.append(f"FORBIDDEN_FOUND: {f}")
            ok = False
        else:
            checks.append(f"forbidden_absent: {f}")
    for r in REQUIRED_IN_TEMPLATES:
        if r in content:
            checks.append(f"required_present: {r}")
        else:
            checks.append(f"REQUIRED_MISSING: {r}")
            ok = False
    return TemplateValidation(path.name, ok, tuple(checks))

def validate_all_templates(deploy_dir: pathlib.Path) -> list[TemplateValidation]:
    results = []
    svc_dir = deploy_dir / "systemd"
    if svc_dir.exists():
        for p in sorted(svc_dir.glob("*.example")):
            results.append(validate_template(p))
    return results

def write_validations(vals: list[TemplateValidation], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([v.to_dict() for v in vals], indent=2), encoding="utf-8")
