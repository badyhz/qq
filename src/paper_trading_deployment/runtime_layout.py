"""Runtime layout — checks and plans runtime directory structure."""
from __future__ import annotations
import pathlib
from src.paper_trading_deployment.models import RuntimeLayoutReport, new_id, utc_now_iso

REQUIRED_DIRS = (
    "data/runtime/paper_trading_pipeline",
    "data/runtime/paper_trading_ops",
    "reports/paper_trading",
    "reports/paper_trading_ops",
    "logs/paper_trading_ops",
)


def check_layout(repo_path: str) -> RuntimeLayoutReport:
    root = pathlib.Path(repo_path)
    existing: list[str] = []
    missing: list[str] = []
    creatable: list[str] = []
    notes: list[str] = []

    for d in REQUIRED_DIRS:
        target = root / d
        if target.exists():
            existing.append(d)
        else:
            missing.append(d)
            # Check if parent exists (can create)
            if target.parent.exists():
                creatable.append(d)
            else:
                notes.append(f"Parent missing for {d}")

    status = "READY" if not missing else ("CREATABLE" if len(creatable) == len(missing) else "INCOMPLETE")

    return RuntimeLayoutReport(
        layout_id=new_id("RLR"), created_at=utc_now_iso(),
        required_dirs=list(REQUIRED_DIRS),
        existing_dirs=existing, missing_dirs=missing,
        creatable_dirs=creatable, layout_status=status, notes=notes,
        final_verdict=f"PAPER_OPS_RUNTIME_LAYOUT_READY|STATUS={status}|EXISTING={len(existing)}|MISSING={len(missing)}|REAL_ORDER_SUBMIT_NOT_ALLOWED",
    )
