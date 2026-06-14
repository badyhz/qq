#!/bin/bash
# Guard: requires ALLOW_GIT_COMMIT=YES, always denies push/tag/deploy
set -euo pipefail

if [ "${ALLOW_GIT_COMMIT:-}" != "YES" ]; then
  echo "BLOCKED: ALLOW_GIT_COMMIT=YES required. Current: '${ALLOW_GIT_COMMIT:-<unset>}'"
  echo "git add + commit are default-deny. Set ALLOW_GIT_COMMIT=YES to proceed."
  exit 1
fi

cd /Users/winnie/Documents/trae_projects/qq
git add core/single_call_recorder.py tests/unit/test_single_call_recorder.py
git commit -m "feat: single call recorder for evidence capture

T762: SingleCallRecorder — records adapter call evidence
- start_record/end_record with auto duration
- approval_token_hash (SHA256, not raw token)
- response_summary truncated to 200 chars
- budget_before/after tracking

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"

# ALWAYS DENY: push/tag/deploy must never run from this script
echo "NOTE: push/tag/deploy are permanently blocked in this script."
