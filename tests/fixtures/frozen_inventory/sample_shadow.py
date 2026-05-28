"""Sample shadow fixture for frozen inventory tests.

This file is NEVER imported or executed by the scanner.
It exists only to test risk keyword detection and category classification.
"""

import csv
import json
from pathlib import Path


def run_shadow_observation(csv_path: str):
    """Read shadow observation data and emit runtime results."""
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def evaluate_shadow_candidate(candidate: dict) -> dict:
    """Score a shadow observation candidate."""
    return {"score": 0.0, "approve": False}
