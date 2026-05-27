"""Report quality crosslink — artifact cross-link validation.

No external URL dependency. No network.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def validate_report_links(
    report_content: str,
    artifact_dir: Path,
) -> Dict[str, Any]:
    """Validate that all artifact links in report resolve to files."""
    import re
    # Find artifact references like [name](name.json) or name.json
    refs = set(re.findall(r'[\w_]+\.json', report_content))
    refs.update(re.findall(r'[\w_]+\.md', report_content))
    refs.update(re.findall(r'[\w_]+\.html', report_content))

    resolved = []
    broken = []
    for ref in sorted(refs):
        if (artifact_dir / ref).exists():
            resolved.append(ref)
        else:
            broken.append(ref)

    return {
        "total_refs": len(refs),
        "resolved": resolved,
        "broken": broken,
        "clean": len(broken) == 0,
        "warning": "" if not broken else f"BROKEN_LINKS:{','.join(broken)}",
    }
