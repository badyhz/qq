#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_FILE="$PROJECT_DIR/automation/artifacts/review_packet.md"

cd "$PROJECT_DIR"

{
  echo "# Review Packet"
  echo
  echo "## Time"
  date
  echo
  echo "## Git Status"
  git status --short
  echo
  echo "## Git Diff Stat"
  git diff --stat
  echo
  echo "## current_task.md"
  echo '```md'
  cat automation/current_task.md 2>/dev/null || true
  echo
  echo '```'
  echo
  echo "## codex_result.md"
  echo '```md'
  cat automation/artifacts/codex_result.md 2>/dev/null || true
  echo
  echo '```'
  echo
  echo "## codex_run.log"
  echo '```text'
  cat automation/artifacts/codex_run.log 2>/dev/null || true
  echo
  echo '```'
  echo
  echo "## validation_report.md"
  echo '```md'
  cat automation/artifacts/validation_report.md 2>/dev/null || true
  echo
  echo '```'
} > "$OUT_FILE"

echo "Built: $OUT_FILE"
