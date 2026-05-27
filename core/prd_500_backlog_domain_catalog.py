"""T901 — 500 backlog domain catalog.

Deterministic. No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Dict, List

from core.prd_task_model import VALID_RISK_LEVELS


@dataclass(frozen=True)
class Prd500BacklogDomain:
    domain_id: str
    title: str
    description: str
    default_risk_level: str
    target_task_count: int
    allowed_file_patterns: List[str]
    forbidden_file_patterns: List[str]
    human_review_required: bool
    notes: List[str]


_BASE_FORBIDDEN = ["secrets", "credentials", "api_keys", ".env"]


def _domain(
    domain_id: str,
    title: str,
    description: str,
    risk: str,
    count: int,
    allowed: List[str],
    extra_forbidden: List[str],
    human_review: bool,
    notes: List[str],
) -> Prd500BacklogDomain:
    if risk not in VALID_RISK_LEVELS:
        raise ValueError(f"Invalid risk level: {risk}")
    forbidden = list(set(_BASE_FORBIDDEN + extra_forbidden))
    forbidden.sort()
    return Prd500BacklogDomain(
        domain_id=domain_id,
        title=title,
        description=description,
        default_risk_level=risk,
        target_task_count=count,
        allowed_file_patterns=list(allowed),
        forbidden_file_patterns=forbidden,
        human_review_required=human_review,
        notes=list(notes),
    )


def build_prd_500_backlog_domain_catalog() -> List[Prd500BacklogDomain]:
    """Returns 10 domains with target_task_count sum >= 500."""
    return [
        _domain(
            "D01_PRD_CONTROL_PLANE",
            "PRD Control Plane",
            "Core control plane modules and dev PRD documents.",
            "LOW",
            80,
            ["core/*.py", "docs/dev_prd/*.md"],
            [],
            False,
            ["Foundation domain — shapes all downstream domains."],
        ),
        _domain(
            "D02_BACKLOG_PLANNING",
            "Backlog Planning",
            "PRD backlog generation, prioritization, and planning tools.",
            "MEDIUM",
            80,
            ["core/prd_*.py"],
            [],
            False,
            ["Feeds tasks into the queue loader."],
        ),
        _domain(
            "D03_READONLY_HOOK_DESIGN",
            "Readonly Hook Design",
            "Design and specification of readonly governance hooks.",
            "LOW",
            60,
            ["core/runtime_governance_readonly_*.py"],
            [],
            False,
            ["No mutation allowed — design only."],
        ),
        _domain(
            "D04_OFFLINE_EVIDENCE_DESIGN",
            "Offline Evidence Design",
            "Evidence collection, recording, and offline audit design.",
            "LOW",
            50,
            ["core/*evidence*.py"],
            [],
            False,
            ["Covers evidence_recorder and related modules."],
        ),
        _domain(
            "D05_MANUAL_REVIEW_CLI_DESIGN",
            "Manual Review CLI Design",
            "CLI tools and review workflow design.",
            "MEDIUM",
            50,
            ["core/*review*.py", "core/*cli*.py"],
            [],
            False,
            ["Human-in-the-loop approval surface."],
        ),
        _domain(
            "D06_READONLY_HOOK_REVIEW",
            "Readonly Hook Review",
            "Review and validation of readonly governance hooks and their tests.",
            "HIGH",
            50,
            [
                "core/runtime_governance_readonly_*.py",
                "tests/unit/test_runtime_governance_readonly_*",
            ],
            [],
            True,
            ["Requires human sign-off before merge."],
        ),
        _domain(
            "D07_RUNTIME_INTEGRATION_REVIEW",
            "Runtime Integration Review",
            "Review of runtime integration across all core modules and tests.",
            "HIGH",
            50,
            ["core/*.py", "tests/unit/*.py"],
            [],
            True,
            ["Cross-cutting review — touches all modules."],
        ),
        _domain(
            "D08_LIVE_EXECUTION_FROZEN",
            "Live Execution (Frozen)",
            "Frozen domain — no live execution tasks permitted.",
            "FROZEN",
            40,
            [],
            [
                "live trading",
                "real order placement",
                "exchange client",
                "planner autonomous",
            ],
            True,
            [
                "FROZEN — no tasks may authorize live execution.",
                "Forbidden patterns block any live-trading file.",
            ],
        ),
        _domain(
            "D09_REGRESSION_AND_CLOSEOUT",
            "Regression and Closeout",
            "Regression test suites and closeout documentation.",
            "LOW",
            50,
            ["tests/unit/*.py", "docs/dev_prd/*.md"],
            [],
            False,
            ["Ensures no regressions across releases."],
        ),
        _domain(
            "D10_ROUTE_AND_AGENT_OPERATIONS",
            "Route and Agent Operations",
            "Automation route definitions and agent operational docs.",
            "MEDIUM",
            40,
            ["automation/*.md", "docs/*.md"],
            [],
            False,
            ["Covers route system and agent playbooks."],
        ),
    ]


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def domain_to_dict(domain: Prd500BacklogDomain) -> Dict:
    """Convert a single domain to a plain dict."""
    return {
        "domain_id": domain.domain_id,
        "title": domain.title,
        "description": domain.description,
        "default_risk_level": domain.default_risk_level,
        "target_task_count": domain.target_task_count,
        "allowed_file_patterns": list(domain.allowed_file_patterns),
        "forbidden_file_patterns": list(domain.forbidden_file_patterns),
        "human_review_required": domain.human_review_required,
        "notes": list(domain.notes),
    }


def domains_to_dict(domains: List[Prd500BacklogDomain]) -> List[Dict]:
    """Convert a list of domains to a list of plain dicts."""
    return [domain_to_dict(d) for d in domains]


def domain_to_markdown(domain: Prd500BacklogDomain) -> str:
    """Render one domain as a markdown block."""
    lines = [
        f"## {domain.domain_id}: {domain.title}",
        "",
        f"**Risk Level:** {domain.default_risk_level}",
        f"**Target Tasks:** {domain.target_task_count}",
        f"**Human Review Required:** {'yes' if domain.human_review_required else 'no'}",
        "",
        domain.description,
        "",
    ]
    if domain.allowed_file_patterns:
        lines.append("**Allowed File Patterns:**")
        for p in domain.allowed_file_patterns:
            lines.append(f"- `{p}`")
        lines.append("")
    if domain.forbidden_file_patterns:
        lines.append("**Forbidden File Patterns:**")
        for p in domain.forbidden_file_patterns:
            lines.append(f"- `{p}`")
        lines.append("")
    if domain.notes:
        lines.append("**Notes:**")
        for n in domain.notes:
            lines.append(f"- {n}")
        lines.append("")
    return "\n".join(lines)


def domains_to_markdown(domains: List[Prd500BacklogDomain]) -> str:
    """Render all domains as a single markdown document."""
    header = [
        "# PRD 500-Backlog Domain Catalog",
        "",
        f"Total domains: {len(domains)}",
        f"Total target tasks: {sum(d.target_task_count for d in domains)}",
        "",
        "---",
        "",
    ]
    body = "\n".join(domain_to_markdown(d) for d in domains)
    return "\n".join(header) + body


def summarize_domain_catalog(domains: List[Prd500BacklogDomain]) -> Dict:
    """Return a summary dict of the domain catalog."""
    risk_counts: Dict[str, int] = {}
    for d in domains:
        risk_counts[d.default_risk_level] = risk_counts.get(d.default_risk_level, 0) + 1
    return {
        "domain_count": len(domains),
        "total_target_tasks": sum(d.target_task_count for d in domains),
        "human_review_domains": sum(1 for d in domains if d.human_review_required),
        "frozen_domains": sum(1 for d in domains if d.default_risk_level == "FROZEN"),
        "risk_level_distribution": risk_counts,
        "domain_ids": [d.domain_id for d in domains],
    }
