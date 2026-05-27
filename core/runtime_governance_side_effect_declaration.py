"""T830 — Side-effect declarations for runtime governance components."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RuntimeGovernanceSideEffectDeclaration:
    component: str
    reads_memory: bool
    writes_memory: bool
    reads_files: bool
    writes_files: bool
    calls_network: bool
    places_orders: bool
    mutates_account: bool
    accesses_secrets: bool
    verdict: str  # "PASS" or "BLOCKED"


_DEFAULT_SAFE = dict(
    reads_memory=True,
    writes_memory=False,
    reads_files=True,
    writes_files=False,
    calls_network=False,
    places_orders=False,
    mutates_account=False,
    accesses_secrets=False,
)


def build_runtime_governance_side_effect_declarations() -> List[RuntimeGovernanceSideEffectDeclaration]:
    """Build declarations for T826-T829. Deterministic."""
    components = [
        ("T826: runtime_governance_contract", {}),
        ("T827: runtime_governance_artifact_index", {}),
        ("T828: runtime_governance_blocker_summary", {}),
        ("T829: runtime_governance_frozen_boundary_map", {}),
    ]
    result = []
    for name, overrides in components:
        fields = {**_DEFAULT_SAFE, **overrides}
        verdict = "PASS"
        for dangerous_key in ("places_orders", "mutates_account", "accesses_secrets"):
            if fields.get(dangerous_key, False):
                verdict = "BLOCKED"
                break
        result.append(RuntimeGovernanceSideEffectDeclaration(
            component=name,
            verdict=verdict,
            **fields,
        ))
    return result


def side_effect_declarations_to_dict(declarations: List[RuntimeGovernanceSideEffectDeclaration]) -> List[Dict[str, Any]]:
    """Serialize."""
    out = []
    for d in declarations:
        out.append({
            "component": d.component,
            "reads_memory": d.reads_memory,
            "writes_memory": d.writes_memory,
            "reads_files": d.reads_files,
            "writes_files": d.writes_files,
            "calls_network": d.calls_network,
            "places_orders": d.places_orders,
            "mutates_account": d.mutates_account,
            "accesses_secrets": d.accesses_secrets,
            "verdict": d.verdict,
        })
    return out


def side_effect_declarations_to_markdown(declarations: List[RuntimeGovernanceSideEffectDeclaration]) -> str:
    """Deterministic markdown."""
    lines = ["# Side-Effect Declarations (T830)", ""]
    lines.append("| Component | R-Mem | W-Mem | R-File | W-File | Network | Orders | Mutate | Secrets | Verdict |")
    lines.append("|-----------|-------|-------|--------|--------|---------|--------|--------|---------|---------|")
    for d in declarations:
        def yn(v: bool) -> str:
            return "Y" if v else "N"
        lines.append(
            f"| {d.component} | {yn(d.reads_memory)} | {yn(d.writes_memory)} | "
            f"{yn(d.reads_files)} | {yn(d.writes_files)} | {yn(d.calls_network)} | "
            f"{yn(d.places_orders)} | {yn(d.mutates_account)} | {yn(d.accesses_secrets)} | "
            f"{d.verdict} |"
        )
    return "\n".join(lines) + "\n"


def summarize_side_effect_declarations(declarations: List[RuntimeGovernanceSideEffectDeclaration]) -> Dict[str, Any]:
    """Summarize."""
    total = len(declarations)
    blocked = sum(1 for d in declarations if d.verdict == "BLOCKED")
    return {
        "total_components": total,
        "pass_count": total - blocked,
        "blocked_count": blocked,
        "all_pass": blocked == 0,
    }
