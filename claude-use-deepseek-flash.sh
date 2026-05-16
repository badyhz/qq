#!/usr/bin/env bash
set -euo pipefail

[ -f ~/.secrets/deepseek.sh ] && source ~/.secrets/deepseek.sh

if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
  echo "ERROR: DEEPSEEK_API_KEY is empty"
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
unset VOLCENGINE_API_KEY

# Force non-thinking / non-reasoning route for flash.
unset CLAUDE_CODE_EFFORT_LEVEL
unset CLAUDE_CODE_REASONING_EFFORT
unset CLAUDE_CODE_BUDGET_TOKENS
unset ANTHROPIC_BUDGET_TOKENS
unset EXTENDED_THINKING

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
export ANTHROPIC_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export ANTHROPIC_SMALL_FAST_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
export BASH_MAX_OUTPUT_LENGTH="12000"

echo "Claude route: deepseek_flash"
echo "DEEPSEEK_API_KEY length: ${#DEEPSEEK_API_KEY}"
echo "ANTHROPIC_MODEL=$ANTHROPIC_MODEL"
