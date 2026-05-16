#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, Optional


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def write_json(path: str, data: Dict[str, Any]) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def generate_validation(
    human_token_packet: Optional[Dict[str, Any]],
    provided_token: Optional[str] = None,
) -> Dict[str, Any]:
    blockers = []
    warnings = []

    if not isinstance(human_token_packet, dict):
        blockers.append("HUMAN_TOKEN_PACKET_MISSING")
        human_token_packet = {}

    token_required = bool(human_token_packet.get("token_required") is True)
    token_scope = human_token_packet.get("token_scope", {})
    expected_token = str(human_token_packet.get("token_phrase_template", ""))

    token_provided = provided_token is not None and len(str(provided_token).strip()) > 0
    token_matches = False

    if token_provided:
        token_matches = str(provided_token).strip() == expected_token.strip()
        if not token_matches:
            blockers.append("TOKEN_MISMATCH")
        else:
            # Check token scope matches
            token_str = str(provided_token).strip()
            parts = token_str.split(":")
            if len(parts) >= 6:
                scope_env = token_scope.get("env", "")
                scope_symbol = token_scope.get("symbol", "")
                scope_side = token_scope.get("side", "")
                scope_qty = str(token_scope.get("quantity", ""))
                scope_count = str(token_scope.get("max_submit_count", ""))
                if parts[1] != scope_env or parts[2] != scope_symbol or parts[3] != scope_side or parts[4] != scope_qty or parts[5] != f"COUNT_{scope_count}":
                    blockers.append("TOKEN_SCOPE_MISMATCH")
            else:
                blockers.append("TOKEN_FORMAT_INVALID")

    if not token_provided:
        verdict = "PARTIAL"
        ok = False
        warnings.append("NO_TOKEN_PROVIDED")
    elif blockers:
        verdict = "FAIL"
        ok = False
    else:
        verdict = "PASS"
        ok = True

    return {
        "ok": ok,
        "verdict": verdict,
        "token_required": token_required,
        "token_provided": token_provided,
        "token_matches": token_matches,
        "token_scope": token_scope,
        "submit_allowed": False,
        "max_submit_count": 1,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Simulate human token validation locally")
    parser.add_argument("--human-token-packet-json", required=True)
    parser.add_argument("--provided-token")
    parser.add_argument("--output-json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    report = generate_validation(
        load_json(args.human_token_packet_json),
        args.provided_token,
    )

    if args.output_json and not write_json(args.output_json, report):
        print("failed_to_write_output", file=sys.stderr)
        return 1
    if args.json:
        if args.pretty:
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
