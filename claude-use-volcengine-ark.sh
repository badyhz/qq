#!/usr/bin/env bash
set -euo pipefail

[ -f ~/.secrets/volcengine.sh ] && source ~/.secrets/volcengine.sh

if [ -z "${VOLCENGINE_API_KEY:-}" ]; then
  echo "ERROR: VOLCENGINE_API_KEY is empty"
  exit 1
fi

unset ANTHROPIC_API_KEY
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

export ANTHROPIC_BASE_URL="https://ark.cn-beijing.volces.com/api/coding"
export ANTHROPIC_AUTH_TOKEN="$VOLCENGINE_API_KEY"
export ANTHROPIC_MODEL="ark-code-latest"
export ANTHROPIC_DEFAULT_OPUS_MODEL="ark-code-latest"
export ANTHROPIC_DEFAULT_SONNET_MODEL="ark-code-latest"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="ark-code-latest"
export ANTHROPIC_SMALL_FAST_MODEL="ark-code-latest"
export CLAUDE_CODE_SUBAGENT_MODEL="ark-code-latest"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
export BASH_MAX_OUTPUT_LENGTH="12000"

echo "Claude route: volcengine_ark"
echo "VOLCENGINE_API_KEY length: ${#VOLCENGINE_API_KEY}"
