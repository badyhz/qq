#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TASK_FILE="$PROJECT_DIR/automation/current_task.md"
REPORT_FILE="$PROJECT_DIR/automation/artifacts/validation_report.md"

cd "$PROJECT_DIR"

TEST_FILE="tests/unit/test_execution.py"

if [ -f "$TASK_FILE" ]; then
  EXTRACTED_TEST_FILE=$(grep "Test file to create:" "$TASK_FILE" | sed 's/.*: //' | head -n 1 | tr -d '`' | xargs || true)
  if [ -n "$EXTRACTED_TEST_FILE" ]; then
    TEST_FILE="$EXTRACTED_TEST_FILE"
  fi
fi

{
  echo "# Validation Report"
  echo
  echo "## Time"
  date
  echo
  echo "## Git Status"
  git status --short
  echo
  echo "## Changed Files"
  git diff --name-only
  echo
  echo "## Test File"
  echo "$TEST_FILE"
  echo
  echo "## Test Command"
  echo "./.venv/bin/python -m pytest $TEST_FILE -v"
  echo
  echo "## Test Output"
  ./.venv/bin/python -m pytest "$TEST_FILE" -v || true
} > "$REPORT_FILE" 2>&1
