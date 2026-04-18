#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TASK_FILE="$PROJECT_DIR/automation/current_task.md"
APPROVAL_FILE="$PROJECT_DIR/automation/approval.json"
RESULT_FILE="$PROJECT_DIR/automation/artifacts/codex_result.md"
LOG_FILE="$PROJECT_DIR/automation/artifacts/codex_run.log"

cd "$PROJECT_DIR"

if ! grep -q '"approved":[[:space:]]*true' "$APPROVAL_FILE"; then
  echo "Task not approved. Stop." | tee -a "$LOG_FILE"
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI not found. Please install or fix PATH first." | tee -a "$LOG_FILE"
  exit 1
fi

echo "=== Codex run started at $(date) ===" | tee -a "$LOG_FILE"

PROMPT="$(cat "$TASK_FILE")"

HTTP_PROXY="http://127.0.0.1:7890" \
HTTPS_PROXY="http://127.0.0.1:7890" \
ALL_PROXY="socks5://127.0.0.1:7890" \
codex exec "$PROMPT" > "$RESULT_FILE" 2>> "$LOG_FILE"

echo "=== Codex run finished at $(date) ===" | tee -a "$LOG_FILE"

./automation/validate_codex.sh
