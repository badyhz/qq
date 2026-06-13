"""T45001 — Repo Hygiene Scanner.

Pure deterministic. No I/O. No network.
Scans codebase patterns for forbidden terms and hygiene violations.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED_RHS = "HOLD"

FORBIDDEN_TERMS = (
    "REAL_SUBMIT_ALLOWED",
    "TESTNET_SUBMIT_ALLOWED",
    "LIVE_TRADING",
    "AUTO_SUBMIT_ENABLED",
)

ALLOWED_CONTEXTS = (
    "FORBIDDEN_",
    "denylist",
    "deny_list",
    "deny-list",
    "forbidden",
)

PRE_COMMIT_CHECKS = (
    {
        "check_id": "forbidden_terms",
        "description": "Detect forbidden trading permission terms outside deny-list contexts",
        "pattern": "|".join(FORBIDDEN_TERMS),
        "severity": "BLOCK",
    },
    {
        "check_id": "hardcoded_secrets",
        "description": "Detect potential hardcoded API keys or secrets",
        "pattern": r"(api_key|api_secret|password)\s*=\s*['\"][^'\"]+['\"]",
        "severity": "BLOCK",
    },
    {
        "check_id": "real_order_calls",
        "description": "Detect real order submission calls outside dry-run context",
        "pattern": r"(create_order|submit_order|place_order)",
        "severity": "WARN",
    },
    {
        "check_id": "live_mode_flag",
        "description": "Detect enable_live_trading=True outside guard context",
        "pattern": r"enable_live_trading\s*=\s*True",
        "severity": "BLOCK",
    },
)


@dataclass(frozen=True)
class HygieneCheck:
    """Single hygiene check definition."""
    check_id: str
    description: str
    pattern: str
    severity: str
    pre_commit_hook_compatible: bool

    def to_dict(self) -> dict:
        return {
            "check_id": self.check_id,
            "description": self.description,
            "pattern": self.pattern,
            "severity": self.severity,
            "pre_commit_hook_compatible": self.pre_commit_hook_compatible,
        }


@dataclass(frozen=True)
class PreCommitHookConfig:
    """Pre-commit hook configuration."""
    config_id: str
    hook_name: str
    checks: tuple[HygieneCheck, ...]
    enabled: bool
    blocking: bool
    description: str

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "hook_name": self.hook_name,
            "checks": [c.to_dict() for c in self.checks],
            "enabled": self.enabled,
            "blocking": self.blocking,
            "description": self.description,
        }


def build_hygiene_check(check_def: dict) -> HygieneCheck:
    """Build a hygiene check from definition."""
    return HygieneCheck(
        check_id=check_def["check_id"],
        description=check_def["description"],
        pattern=check_def["pattern"],
        severity=check_def["severity"],
        pre_commit_hook_compatible=True,
    )


def build_pre_commit_config() -> PreCommitHookConfig:
    """Build pre-commit hook configuration."""
    checks = tuple(build_hygiene_check(c) for c in PRE_COMMIT_CHECKS)
    return PreCommitHookConfig(
        config_id="pre_commit_hygiene_v1",
        hook_name="qq-hygiene-check",
        checks=checks,
        enabled=True,
        blocking=True,
        description="Pre-commit hook to detect forbidden trading terms and security violations",
    )


def compute_config_hash(config: PreCommitHookConfig) -> str:
    raw = json.dumps(config.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_pre_commit_config_markdown(config: PreCommitHookConfig) -> str:
    lines = [
        "# Pre-commit Hook Configuration",
        "",
        f"- **Hook name:** {config.hook_name}",
        f"- **Enabled:** {config.enabled}",
        f"- **Blocking:** {config.blocking}",
        f"- **Description:** {config.description}",
        "",
        "## Checks",
        "",
    ]
    for c in config.checks:
        lines.append(f"### {c.check_id}")
        lines.append(f"- **Description:** {c.description}")
        lines.append(f"- **Severity:** {c.severity}")
        lines.append(f"- **Pattern:** `{c.pattern}`")
        lines.append(f"- **Pre-commit compatible:** {c.pre_commit_hook_compatible}")
        lines.append("")
    return "\n".join(lines)


def render_hygiene_report_markdown() -> str:
    """Render repo hygiene report."""
    lines = [
        "# Repo Hygiene Report",
        "",
        "## Forbidden Terms Policy",
        "",
        "The following terms are forbidden outside deny-list contexts:",
        "",
    ]
    for t in FORBIDDEN_TERMS:
        lines.append(f"- `{t}`")

    lines.append("")
    lines.append("## Allowed Contexts")
    lines.append("")
    lines.append("Forbidden terms may appear in:")
    for c in ALLOWED_CONTEXTS:
        lines.append(f"- `{c}`")

    lines.append("")
    lines.append("## Pre-commit Hook Checks")
    lines.append("")
    for c in PRE_COMMIT_CHECKS:
        lines.append(f"- **{c['check_id']}** [{c['severity']}]: {c['description']}")

    lines.append("")
    lines.append("## Recommended .pre-commit-config.yaml")
    lines.append("")
    lines.append("```yaml")
    lines.append("repos:")
    lines.append("  - repo: local")
    lines.append("    hooks:")
    lines.append("      - id: qq-hygiene-check")
    lines.append("        name: QQ Hygiene Check")
    lines.append("        entry: python scripts/check_repo_hygiene.py")
    lines.append("        language: system")
    lines.append("        always_run: true")
    lines.append("        pass_filenames: false")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def write_json(config: PreCommitHookConfig, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")


def write_manifest(config: PreCommitHookConfig, out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "config_id": config.config_id,
        "hook_name": config.hook_name,
        "enabled": config.enabled,
        "blocking": config.blocking,
        "checks_count": len(config.checks),
        "release_hold": release_hold,
        "config_hash": compute_config_hash(config),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
