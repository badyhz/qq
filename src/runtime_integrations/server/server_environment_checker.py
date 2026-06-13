"""Server environment checker. Validates local/server readiness."""
from __future__ import annotations
import json, pathlib, sys
from dataclasses import dataclass

@dataclass(frozen=True)
class EnvironmentCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def check_environment(root: pathlib.Path) -> list[EnvironmentCheck]:
    checks = []
    # Python version
    v = sys.version_info
    checks.append(EnvironmentCheck("python_version", v >= (3, 9), f"{v.major}.{v.minor}.{v.micro}"))
    # Repository path
    checks.append(EnvironmentCheck("repo_path", (root / "src" / "runtime_integrations").exists(), str(root)))
    # Expected scripts
    for s in ("run_system_dry_run_e2e.py", "run_runtime_stabilization_suite.py"):
        checks.append(EnvironmentCheck(f"script_{s.replace('.py','')}", (root / "scripts" / s).exists(), s))
    # Import check
    try:
        from src.runtime_integrations.e2e.system_dry_run_e2e import run_e2e
        checks.append(EnvironmentCheck("import_e2e", True, "importable"))
    except ImportError as e:
        checks.append(EnvironmentCheck("import_e2e", False, str(e)))
    # Deployment templates
    for f in ("README.md", "env.example", "safety_checklist.md"):
        checks.append(EnvironmentCheck(f"deploy_{f.replace('.','_')}", (root / "deployment" / "runtime_dry_run" / f).exists(), f))
    # No real secrets
    env_example = root / "deployment" / "runtime_dry_run" / "env.example"
    if env_example.exists():
        content = env_example.read_text()
        checks.append(EnvironmentCheck("no_real_secrets", "REAL_API_KEY" not in content and "sk-" not in content, "env.example clean"))
    return checks

def write_checks(checks: list[EnvironmentCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
