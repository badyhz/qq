#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Reuse flash env setup, keep non-thinking/non-reasoning defaults.
source "$SCRIPT_DIR/claude-use-deepseek-flash.sh"

export ANTHROPIC_MODEL="deepseek-v4-flash"
unset CLAUDE_CODE_EFFORT_LEVEL
unset CLAUDE_CODE_REASONING_EFFORT
unset CLAUDE_CODE_BUDGET_TOKENS
unset ANTHROPIC_BUDGET_TOKENS
unset EXTENDED_THINKING

echo "Claude route: deepseek_flash_full"
echo "DEEPSEEK_API_KEY length: ${#DEEPSEEK_API_KEY}"
echo "ANTHROPIC_MODEL=$ANTHROPIC_MODEL"

exec claude --permission-mode bypassPermissions --dangerously-skip-permissions "$@"
