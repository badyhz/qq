"""Sample testnet fixture for frozen inventory tests.

This file is NEVER imported or executed by the scanner.
It exists only to test risk keyword detection and category classification.

Contains risk keywords: testnet, positionRisk, fapi, requests
"""

import os

CREDENTIAL_PLACEHOLDER_A = os.getenv("CREDENTIAL_PLACEHOLDER_A", "")

def check_testnet_state(symbol: str) -> dict:
    """Check testnet position state via FAPI endpoint."""
    import requests  # noqa: F401
    # fapi/v2/positionRisk endpoint
    return {}
