#!/bin/bash
cd /Users/winnie/Documents/trae_projects/qq
git add core/single_call_recorder.py tests/unit/test_single_call_recorder.py
git commit -m "feat: single call recorder for evidence capture

T762: SingleCallRecorder — records adapter call evidence
- start_record/end_record with auto duration
- approval_token_hash (SHA256, not raw token)
- response_summary truncated to 200 chars
- budget_before/after tracking

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
