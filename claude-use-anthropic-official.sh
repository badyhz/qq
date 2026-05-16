#!/usr/bin/env bash
set -euo pipefail

[ -f ~/.secrets/anthropic.sh ] && source ~/.secrets/anthropic.sh

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is empty"
  exit 1
fi

unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN
unset CLAUDE_CODE_USE_VERTEX
unset CLAUDE_CODE_USE_BEDROCK
unset ANTHROPIC_VERTEX_PROJECT_ID
unset ANTHROPIC_VERTEX_REGION
unset CLOUD_ML_REGION
unset GOOGLE_APPLICATION_CREDENTIALS
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY
unset AWS_SESSION_TOKEN
unset AWS_PROFILE

export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
export BASH_MAX_OUTPUT_LENGTH="12000"

echo "Claude route: anthropic_official"
echo "ANTHROPIC_API_KEY length: ${#ANTHROPIC_API_KEY}"
