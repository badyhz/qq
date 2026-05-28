"""Research fixture loader — deterministic fixture loading and validation.

Loads JSON fixtures from research_quality fixture directories.
Deterministic ordering. Validates required fields. Produces stable hashes.
No network. No large file loads.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


FIXTURE_ROOT = Path("tests/fixtures/research_quality")

REQUIRED_BASE_FIELDS = ("schema_version", "fixture_type")
REQUIRED_BAR_FIELDS = ("timestamp", "open", "high", "low", "close", "volume")
REQUIRED_SPLIT_FIELDS = ("split_id", "train_start", "train_end", "test_start", "test_end")


class FixtureLoadError(Exception):
    """Raised when fixture loading fails."""
    pass


def load_fixture(path: Path) -> Dict[str, Any]:
    """Load a single JSON fixture file.

    Args:
        path: Path to JSON fixture file.

    Returns:
        Parsed fixture dict.

    Raises:
        FixtureLoadError: If file missing, unparseable, or malformed.
    """
    if not path.exists():
        raise FixtureLoadError(f"Fixture not found: {path}")

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, ValueError) as e:
        raise FixtureLoadError(f"Invalid JSON in {path}: {e}")

    if not isinstance(data, dict):
        raise FixtureLoadError(f"Fixture must be dict, got {type(data).__name__}: {path}")

    for field in REQUIRED_BASE_FIELDS:
        if field not in data:
            raise FixtureLoadError(f"Missing required field '{field}' in {path}")

    return data


def load_fixture_by_name(
    fixture_class: str,
    name: str,
    subdirectory: str = "",
    root: Path = None,
) -> Dict[str, Any]:
    """Load fixture by class and filename.

    Args:
        fixture_class: One of base, adversarial, negative_control, regime, bootstrap, expected.
        name: Filename (e.g. 'clean_ohlcv_btcusdt_5m.json').
        subdirectory: Optional subdirectory within class.
        root: Override fixture root directory.

    Returns:
        Parsed fixture dict.
    """
    base = root or FIXTURE_ROOT
    path = base / fixture_class
    if subdirectory:
        path = path / subdirectory
    path = path / name
    return load_fixture(path)


def load_all_fixtures_in_dir(directory: Path) -> Tuple[Dict[str, Any], ...]:
    """Load all JSON fixtures in a directory, sorted by filename.

    Args:
        directory: Directory to scan.

    Returns:
        Tuple of parsed fixture dicts, sorted by filename.
    """
    if not directory.exists():
        return ()

    fixtures = []
    for p in sorted(directory.glob("*.json")):
        try:
            fixtures.append(load_fixture(p))
        except FixtureLoadError:
            continue
    return tuple(fixtures)


def validate_fixture_bars(bars: List[Dict[str, Any]]) -> List[str]:
    """Validate OHLCV bars have required fields.

    Args:
        bars: List of bar dicts.

    Returns:
        List of validation error strings (empty if valid).
    """
    errors = []
    for i, bar in enumerate(bars):
        for field in REQUIRED_BAR_FIELDS:
            if field not in bar:
                errors.append(f"Bar {i}: missing field '{field}'")
            elif bar[field] is None:
                errors.append(f"Bar {i}: null value for '{field}'")
    return errors


def validate_fixture_splits(splits: List[Dict[str, Any]]) -> List[str]:
    """Validate splits have required fields.

    Args:
        splits: List of split dicts.

    Returns:
        List of validation error strings (empty if valid).
    """
    errors = []
    for i, split in enumerate(splits):
        for field in REQUIRED_SPLIT_FIELDS:
            if field not in split:
                errors.append(f"Split {i}: missing field '{field}'")
    return errors


def fixture_hash(data: Dict[str, Any]) -> str:
    """Compute stable SHA-256 hash of fixture content.

    Args:
        data: Fixture dict.

    Returns:
        Hex digest string.
    """
    stable = json.dumps(data, sort_keys=True, indent=2, default=str)
    return hashlib.sha256(stable.encode()).hexdigest()


def discover_fixture_files(root: Path = None) -> Dict[str, List[str]]:
    """Discover all fixture files grouped by class.

    Args:
        root: Override fixture root directory.

    Returns:
        Dict mapping fixture class to sorted list of relative file paths.
    """
    base = root or FIXTURE_ROOT
    result = {}
    for cls_dir in sorted(base.iterdir()):
        if not cls_dir.is_dir():
            continue
        files = []
        for p in sorted(cls_dir.rglob("*.json")):
            files.append(str(p.relative_to(cls_dir)))
        if files:
            result[cls_dir.name] = files
    return result
