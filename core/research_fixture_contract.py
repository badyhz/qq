"""Research fixture contract — fixture layout and discovery.

Defines fixture classes: base, adversarial, negative_control, regime, bootstrap, expected.
No network. No full-file loads.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

FIXTURE_CLASSES = (
    "base", "adversarial", "negative_control",
    "regime", "bootstrap", "expected",
)

FIXTURE_SUBDIRS: Dict[str, Tuple[str, ...]] = {
    "adversarial": ("data_quality", "split_leakage", "parameter_robustness", "portfolio_robustness"),
    "expected": ("data_quality", "split_oos", "parameter_robustness", "strategy_robustness",
                 "portfolio_robustness", "negative_control", "bootstrap_regime", "report_quality",
                 "final_acceptance"),
}


@dataclass(frozen=True)
class FixtureInfo:
    """Fixture discovery result."""
    fixture_class: str
    subdirectory: str
    path: str
    exists: bool
    file_count: int


def discover_fixtures(base_dir: Path) -> Tuple[FixtureInfo, ...]:
    """Discover all fixture classes under base_dir."""
    results = []
    for cls in FIXTURE_CLASSES:
        cls_dir = base_dir / cls
        exists = cls_dir.exists()
        count = len(list(cls_dir.glob("*"))) if exists else 0
        subdirs = FIXTURE_SUBDIRS.get(cls, ())
        if subdirs:
            for sub in subdirs:
                sub_path = cls_dir / sub
                sub_exists = sub_path.exists()
                sub_count = len(list(sub_path.glob("*"))) if sub_exists else 0
                results.append(FixtureInfo(cls, sub, str(sub_path), sub_exists, sub_count))
        else:
            results.append(FixtureInfo(cls, "", str(cls_dir), exists, count))
    return tuple(results)


def validate_fixture_integrity(base_dir: Path) -> List[str]:
    """Validate fixture directory integrity. Returns list of issues."""
    issues = []
    for cls in FIXTURE_CLASSES:
        cls_dir = base_dir / cls
        if not cls_dir.exists():
            issues.append(f"Missing fixture class directory: {cls}")
        else:
            subdirs = FIXTURE_SUBDIRS.get(cls, ())
            if subdirs:
                for sub in subdirs:
                    sub_path = cls_dir / sub
                    if not sub_path.exists():
                        issues.append(f"Missing fixture subdirectory: {cls}/{sub}")
    return issues
