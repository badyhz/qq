#!/usr/bin/env python3
"""T1891-T1900 - CLI to generate frozen backlog agent handoff prompt.

Reads FROZEN_BACKLOG_INVENTORY, generates report summary,
calls generate_agent_handoff, writes markdown to --output-md.

Usage:
    python scripts/generate_frozen_backlog_agent_handoff.py --output-md PATH

Exit 0 on success.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.frozen_backlog_agent_handoff_generator import generate_agent_handoff
from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_report_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate frozen backlog agent handoff prompt",
    )
    parser.add_argument(
        "--output-md",
        required=True,
        help="Output path for the markdown handoff prompt",
    )
    args = parser.parse_args()

    inventory = FROZEN_BACKLOG_INVENTORY
    summary = materialize_report_summary(inventory)
    handoff_md = generate_agent_handoff(inventory, summary)

    output_path = Path(args.output_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(handoff_md, encoding="utf-8")

    print(f"Agent handoff written to {output_path}")
    print(f"Frozen files: {inventory.total_count}")
    print(f"Exit: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
