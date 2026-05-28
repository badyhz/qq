#!/usr/bin/env python3
"""Build offline research operator bundle.

No network. No exchange. No runtime. No planner. Advisory only.
release_hold must remain HOLD. Standalone offline HTML.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.offline_research_experiment_library import load_experiment_catalog
from core.offline_research_governance import (
    REQUIRED_OPERATOR_MANUALS,
    REQUIRED_RUNBOOKS,
    REQUIRED_CHECKLISTS,
    REQUIRED_RECOVERY_DOCS,
    check_file_exists,
)


def build_index(docs_root: Path, catalog_path: Path) -> dict:
    """Build operator bundle index."""
    operator_manuals = [r for r in REQUIRED_OPERATOR_MANUALS if check_file_exists(docs_root, r)]
    runbooks = [r for r in REQUIRED_RUNBOOKS if check_file_exists(docs_root, r)]
    checklists = [r for r in REQUIRED_CHECKLISTS if check_file_exists(docs_root, r)]
    recovery = [r for r in REQUIRED_RECOVERY_DOCS if check_file_exists(docs_root, r)]

    catalog = load_experiment_catalog(catalog_path)
    experiment_count = len(catalog.get("experiments", []))

    return {
        "version": "1.0.0",
        "generated_by": "offline_research_operator_bundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_hold": "HOLD",
        "advisory_only": True,
        "human_review_required": True,
        "operator_manuals": operator_manuals,
        "runbooks": runbooks,
        "checklists": checklists,
        "recovery_docs": recovery,
        "experiment_count": experiment_count,
        "total_docs": len(operator_manuals) + len(runbooks) + len(checklists) + len(recovery),
    }


def build_manifest(index: dict) -> dict:
    """Build operator bundle manifest."""
    return {
        "version": "1.0.0",
        "generated_by": "offline_research_operator_bundle",
        "generated_at": index["generated_at"],
        "release_hold": "HOLD",
        "advisory_only": True,
        "doc_counts": {
            "operator_manuals": len(index["operator_manuals"]),
            "runbooks": len(index["runbooks"]),
            "checklists": len(index["checklists"]),
            "recovery_docs": len(index["recovery_docs"]),
            "experiments": index["experiment_count"],
            "total": index["total_docs"],
        },
    }


def build_markdown(index: dict) -> str:
    """Build operator bundle markdown."""
    lines = [
        "# Offline Research Operator Bundle",
        "",
        f"**Generated:** {index['generated_at']}",
        f"**release_hold:** HOLD",
        f"**advisory_only:** true",
        "",
        "## Operator Manuals",
        "",
    ]
    for doc in index["operator_manuals"]:
        lines.append(f"- `{doc}`")
    lines.extend(["", "## Runbooks", ""])
    for doc in index["runbooks"]:
        lines.append(f"- `{doc}`")
    lines.extend(["", "## Checklists", ""])
    for doc in index["checklists"]:
        lines.append(f"- `{doc}`")
    lines.extend(["", "## Recovery Docs", ""])
    for doc in index["recovery_docs"]:
        lines.append(f"- `{doc}`")
    lines.extend([
        "",
        f"## Experiments: {index['experiment_count']}",
        "",
        f"Total docs: {index['total_docs']}",
        "",
        "## Safety",
        "",
        "- Offline only. No network. No exchange.",
        "- release_hold = HOLD",
        "- Advisory only. Human review required.",
        "- No live/testnet/runtime/planner integration.",
        "- No auto-promotion.",
    ])
    return "\n".join(lines)


def build_html(index: dict) -> str:
    """Build standalone offline HTML bundle."""
    manuals_html = "".join(f"<li>{d}</li>" for d in index["operator_manuals"])
    runbooks_html = "".join(f"<li>{d}</li>" for d in index["runbooks"])
    checklists_html = "".join(f"<li>{d}</li>" for d in index["checklists"])
    recovery_html = "".join(f"<li>{d}</li>" for d in index["recovery_docs"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Offline Research Operator Bundle</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #1a1a1a; }}
h2 {{ color: #333; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
ul {{ line-height: 1.8; }}
.safety {{ background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 4px; margin: 16px 0; }}
.meta {{ color: #666; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Offline Research Operator Bundle</h1>
<p class="meta">Generated: {index['generated_at']}</p>
<p class="meta">release_hold: HOLD | advisory_only: true | human_review_required: true</p>

<div class="safety">
<strong>Safety Boundary:</strong> Offline only. No network. No exchange. No live/testnet/runtime/planner.
release_hold = HOLD. No auto-promotion. Advisory only. Human review required.
</div>

<h2>Operator Manuals ({len(index['operator_manuals'])})</h2>
<ul>{manuals_html}</ul>

<h2>Runbooks ({len(index['runbooks'])})</h2>
<ul>{runbooks_html}</ul>

<h2>Checklists ({len(index['checklists'])})</h2>
<ul>{checklists_html}</ul>

<h2>Recovery Docs ({len(index['recovery_docs'])})</h2>
<ul>{recovery_html}</ul>

<h2>Experiments ({index['experiment_count']})</h2>
<p>Total documentation artifacts: {index['total_docs']}</p>

<h2>Command Cheatsheet</h2>
<pre>
# Validate experiment library
python3 scripts/validate_offline_research_experiment_library.py \\
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \\
  --output-dir /tmp/offline_research_experiment_library_validation \\
  --strict --release-hold HOLD

# Validate docs governance
python3 scripts/validate_offline_research_stack_docs.py \\
  --docs-root docs \\
  --output-dir /tmp/offline_research_governance_validation \\
  --strict --release-hold HOLD

# Build operator bundle
python3 scripts/build_offline_research_operator_bundle.py \\
  --docs-root docs \\
  --experiment-catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \\
  --output-dir /tmp/offline_research_operator_bundle \\
  --strict --release-hold HOLD

# Run full test suite
PYTHONPATH=. .venv/bin/pytest -q
</pre>

<h2>Recovery Index</h2>
<ul>
<li>Missing artifacts: See <code>recovery/missing_quality_artifacts_recovery.md</code></li>
<li>Corrupted JSON: See <code>recovery/corrupted_json_recovery.md</code></li>
<li>Reproducibility mismatch: See <code>recovery/reproducibility_mismatch_recovery.md</code></li>
<li>Invalid safety flags: See <code>recovery/invalid_safety_flags_recovery.md</code></li>
<li>Failed full suite: See <code>recovery/failed_full_suite_recovery.md</code></li>
</ul>
</body>
</html>"""


def build_command_cheatsheet() -> str:
    """Build command cheatsheet markdown."""
    return """# Offline Research Command Cheatsheet

## Validate Experiment Library
```bash
python3 scripts/validate_offline_research_experiment_library.py \\
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \\
  --output-dir /tmp/offline_research_experiment_library_validation \\
  --strict --release-hold HOLD
```

## Validate Docs Governance
```bash
python3 scripts/validate_offline_research_stack_docs.py \\
  --docs-root docs \\
  --output-dir /tmp/offline_research_governance_validation \\
  --strict --release-hold HOLD
```

## Build Operator Bundle
```bash
python3 scripts/build_offline_research_operator_bundle.py \\
  --docs-root docs \\
  --experiment-catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \\
  --output-dir /tmp/offline_research_operator_bundle \\
  --strict --release-hold HOLD
```

## Run Full Test Suite
```bash
PYTHONPATH=. .venv/bin/pytest -q
```

## Run Offline Research Workbench
```bash
python3 scripts/run_multi_strategy_research_workbench.py \\
  --fixture-dir tests/fixtures/historical_backtest_lab \\
  --output-dir /tmp/multi_strategy_research_workbench \\
  --strategies breakout,mean_reversion,momentum,volatility_compression \\
  --symbols BTCUSDT,ETHUSDT \\
  --timeframes 5m,15m \\
  --split-mode rolling \\
  --search-budget 120 \\
  --chunk-size 25
```

## Run Quality Gate
```bash
python3 scripts/run_multi_strategy_research_quality_gate.py \\
  --input-dir /tmp/multi_strategy_research_workbench \\
  --output-dir /tmp/multi_strategy_research_quality_gate \\
  --deterministic-seed 424242 \\
  --strict --release-hold HOLD
```

## Build Artifact Browser
```bash
python3 scripts/build_research_artifact_browser.py \\
  --quality-dir /tmp/multi_strategy_research_quality_gate \\
  --output-dir /tmp/research_artifact_browser \\
  --strict --release-hold HOLD
```

## Build Comparison Analytics
```bash
python3 scripts/build_research_comparison_analytics.py \\
  --bundle baseline=/tmp/research_artifact_browser \\
  --bundle candidate=/tmp/research_artifact_browser \\
  --output-dir /tmp/research_comparison_analytics \\
  --strict --release-hold HOLD
```

## Build Human Review Packet
```bash
python3 scripts/build_research_human_review_packet.py \\
  --quality-dir /tmp/multi_strategy_research_quality_gate \\
  --artifact-browser-dir /tmp/research_artifact_browser \\
  --comparison-dir /tmp/research_comparison_analytics \\
  --output-dir /tmp/research_human_review_packet \\
  --strict --release-hold HOLD
```

## Validate Human Review Packet
```bash
python3 scripts/validate_research_human_review_packet.py \\
  --review-dir /tmp/research_human_review_packet \\
  --strict --release-hold HOLD
```
"""


def build_safety_cheatsheet() -> str:
    """Build safety cheatsheet markdown."""
    return """# Offline Research Safety Cheatsheet

## release_hold
- **MUST be HOLD**
- Never change to RELEASE without explicit human approval
- All scripts require --release-hold HOLD

## Advisory Only
- All research output is advisory only
- No artifact authorizes live trading
- No artifact authorizes testnet submission
- No artifact authorizes runtime activation

## Human Review Required
- All research artifacts require human review
- No auto-promotion mechanism exists
- Allowed decisions: REJECT, REQUEST_MORE_RESEARCH, ACCEPT_ADVISORY_RESEARCH_ONLY
- Forbidden decisions: APPROVE_LIVE, APPROVE_TESTNET_SUBMIT, APPROVE_RUNTIME

## Forbidden Actions
- No network calls (requests, httpx, aiohttp, urllib, websocket)
- No exchange clients (binance, ccxt)
- No order operations (submit, cancel, flatten, place)
- No live trading
- No testnet submission
- No runtime integration
- No planner integration
- No auto-promotion

## Untracked External State
- Pre-existing untracked live/testnet/shadow files are external state
- Do not stage, import, execute, or modify them
- Do not use `git add .`
- Use explicit `git add <file>` only

## Emergency
- If safety boundary is violated: STOP immediately
- Run governance validator to assess damage
- See recovery docs for remediation steps
- Escalate to human operator
"""


def build_recovery_index() -> str:
    """Build recovery index markdown."""
    return """# Offline Research Recovery Index

## Quick Recovery Links

| Issue | Recovery Doc |
|-------|-------------|
| Missing quality artifacts | `recovery/missing_quality_artifacts_recovery.md` |
| Corrupted JSON | `recovery/corrupted_json_recovery.md` |
| Reproducibility mismatch | `recovery/reproducibility_mismatch_recovery.md` |
| Invalid safety flags | `recovery/invalid_safety_flags_recovery.md` |
| Missing review packet | `recovery/missing_review_packet_recovery.md` |
| Failed full suite | `recovery/failed_full_suite_recovery.md` |
| Untracked external state | `recovery/untracked_external_state_recovery.md` |
| Bad commit | `recovery/bad_commit_recovery.md` |
| Restore to tags | `recovery/restore_to_tags_recovery.md` |

## General Recovery Steps
1. Identify the symptom
2. Find the matching recovery doc
3. Follow the inspect commands
4. Apply safe recovery commands only
5. Never use forbidden recovery commands
6. Run final verification
7. If unresolvable, escalate to human operator
"""


def build_experiment_catalog_summary(catalog_path: Path) -> str:
    """Build experiment catalog summary markdown."""
    catalog = load_experiment_catalog(catalog_path)
    experiments = catalog.get("experiments", [])
    lines = [
        "# Offline Research Experiment Catalog Summary",
        "",
        f"**Total experiments:** {len(experiments)}",
        f"**release_hold:** HOLD",
        f"**advisory_only:** true",
        "",
        "| ID | Label | Strategies | Symbols | Timeframes |",
        "|----|-------|-----------|---------|------------|",
    ]
    for exp in experiments:
        strategies = ", ".join(exp["strategy_set"])
        symbols = ", ".join(exp["symbols"])
        timeframes = ", ".join(exp["timeframes"])
        lines.append(f"| {exp['experiment_id']} | {exp['label']} | {strategies} | {symbols} | {timeframes} |")
    lines.extend([
        "",
        "## Safety Flags (All Experiments)",
        "",
        "- release_hold = HOLD",
        "- advisory_only = true",
        "- human_review_required = true",
        "- no_live = true",
        "- no_submit = true",
        "- no_exchange = true",
        "- no_network = true",
        "- no_runtime_integration = true",
        "- no_planner_integration = true",
        "",
        "## Forbidden Commands (All Experiments)",
        "",
        "- submit_order",
        "- cancel_order",
        "- flatten_position",
        "- live_trading",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build offline research operator bundle"
    )
    parser.add_argument(
        "--docs-root", required=True, type=Path,
        help="Root directory of docs"
    )
    parser.add_argument(
        "--experiment-catalog", required=True, type=Path,
        help="Path to experiment catalog JSON"
    )
    parser.add_argument(
        "--output-dir", required=True, type=Path,
        help="Output directory for operator bundle"
    )
    parser.add_argument(
        "--strict", action="store_true", default=False,
        help="Enable strict validation mode"
    )
    parser.add_argument(
        "--release-hold", default="HOLD", type=str,
        help="Expected release_hold value (must be HOLD)"
    )
    args = parser.parse_args()

    if args.release_hold != "HOLD":
        print(f"ERROR: release_hold must be HOLD, got {args.release_hold}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)

    index = build_index(args.docs_root, args.experiment_catalog)
    manifest = build_manifest(index)
    md = build_markdown(index)
    html = build_html(index)
    cmd_sheet = build_command_cheatsheet()
    safety_sheet = build_safety_cheatsheet()
    recovery_idx = build_recovery_index()
    exp_summary = build_experiment_catalog_summary(args.experiment_catalog)

    # Write all artifacts
    artifacts = {
        "operator_bundle_index.json": json.dumps(index, indent=2, sort_keys=True),
        "operator_bundle_manifest.json": json.dumps(manifest, indent=2, sort_keys=True),
        "operator_bundle.md": md,
        "operator_bundle.html": html,
        "command_cheatsheet.md": cmd_sheet,
        "safety_cheatsheet.md": safety_sheet,
        "recovery_index.md": recovery_idx,
        "experiment_catalog_summary.md": exp_summary,
    }

    for name, content in artifacts.items():
        (args.output_dir / name).write_text(content)

    print(f"PASS: Operator bundle built in {args.output_dir}")
    print(f"  Artifacts: {len(artifacts)}")
    print(f"  Docs: {index['total_docs']}")
    print(f"  Experiments: {index['experiment_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
