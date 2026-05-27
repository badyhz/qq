# Verification Script High-Risk Import Policy

**Task ID:** T1282
**release_hold:** HOLD
**Status:** Active

## Policy

Verification scripts MUST NOT import high-risk modules directly.

## Blocked Imports

| Module | Reason |
|--------|--------|
| `ccxt` | Exchange client — can submit orders |
| `requests` (unmocked) | Can make live HTTP calls |
| `websocket` | Can open live connections |
| `boto3` / cloud SDKs | Can mutate cloud state |
| `subprocess` (unaudited) | Can spawn arbitrary processes |

## Allowed Imports

- `json`, `os`, `sys`, `pathlib`, `datetime`, `typing` — standard lib
- `unittest.mock`, `pytest` — testing frameworks
- Project modules ONLY if mocked at import boundary

## Review Checklist

1. Run `grep -n 'import ccxt\|import requests\|import websocket' script.py`
2. Confirm zero hits or all hits inside `with patch(...)` blocks
3. Flag any `__import__()` or `importlib` dynamic loading
4. Verify no `exec()` or `eval()` on external input

## Enforcement

- Any blocked import without mock = REJECT
- Dynamic imports without justification = REJECT
- Escalate to human reviewer if import intent is ambiguous
