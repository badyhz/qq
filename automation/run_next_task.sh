#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
QUEUE_FILE="$PROJECT_DIR/automation/task_queue.md"
TASK_FILE="$PROJECT_DIR/automation/current_task.md"
APPROVAL_FILE="$PROJECT_DIR/automation/approval.json"
RESULT_FILE="$PROJECT_DIR/automation/artifacts/codex_result.md"
VALIDATION_FILE="$PROJECT_DIR/automation/artifacts/validation_report.md"
RUN_CODEX_SCRIPT="$PROJECT_DIR/automation/run_codex.sh"
REVIEW_PACKET_SCRIPT="$PROJECT_DIR/automation/build_review_packet.sh"

canonical_path() {
  local path="$1"
  local dir
  local base

  dir="$(cd "$(dirname "$path")" && pwd -P)"
  base="$(basename "$path")"
  printf '%s/%s\n' "$dir" "$base"
}

assert_allowed_script() {
  local script_path="$1"
  local expected_rel="$2"
  local required="${3:-required}"
  local expected_abs
  local actual_abs

  expected_abs="$PROJECT_DIR/$expected_rel"
  actual_abs="$(canonical_path "$script_path")"

  if [ "$actual_abs" != "$expected_abs" ]; then
    echo "ERROR: script path outside allowlist: $actual_abs"
    exit 1
  fi

  if [ "$required" = "required" ] && [ ! -x "$actual_abs" ]; then
    echo "ERROR: required script missing or not executable: $actual_abs"
    exit 1
  fi
}

cd "$PROJECT_DIR"

assert_allowed_script "$RUN_CODEX_SCRIPT" "automation/run_codex.sh" "required"
assert_allowed_script "$REVIEW_PACKET_SCRIPT" "automation/build_review_packet.sh" "optional"

if [ ! -f "$QUEUE_FILE" ]; then
  echo "task_queue.md not found"
  exit 1
fi

NEXT_TASK=$(awk '
  /^## NEXT/ {in_next=1; next}
  /^## / && $0 !~ /^## NEXT/ {if (in_next) exit}
  in_next {print}
' "$QUEUE_FILE" | sed '/^[[:space:]]*$/d')

if [ -z "$NEXT_TASK" ]; then
  echo "No task found under ## NEXT"
  exit 1
fi

trim_value() {
  printf '%s\n' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/^`+//; s/`+$//'
}

is_placeholder_value() {
  local normalized

  normalized="$(printf '%s\n' "$1" | tr '[:upper:]' '[:lower:]')"

  case "$normalized" in
    ""|"..."|"…"|"-"|"--"|"n/a"|"na"|"none"|"null"|"todo"|"tbd"|"待补充"|"未提供") return 0 ;;
    *) return 1 ;;
  esac
}

is_path_like_value() {
  local value="$1"
  local basename

  value="$(trim_value "$value")"

  [ -n "$value" ] || return 1
  is_placeholder_value "$value" && return 1

  case "$value" in
    *$'\n'*|*$'\r'*|*[[:space:]]*|*://*|*/|*[\*\?\<\>\|\;\：\，\。\（\）]*)
      return 1
      ;;
  esac

  case "$value" in
    */*)
      return 0
      ;;
  esac

  basename="${value##*/}"

  case "$basename" in
    *.*|Dockerfile|Makefile|README|LICENSE)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_valid_doc_path() {
  local path="$1"

  is_path_like_value "$path" || return 1

  case "$path" in
    *.md|*.mdx|*.rst|*.txt|*.adoc)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_valid_source_file_path() {
  local path="$1"

  is_path_like_value "$path" || return 1

  case "$path" in
    *.py)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_valid_test_file_path() {
  local path="$1"
  local basename

  is_path_like_value "$path" || return 1

  case "$path" in
    *.py)
      ;;
    *)
      return 1
      ;;
  esac

  basename="$(basename "$path")"

  case "$path" in
    tests/*|*/tests/*)
      return 0
      ;;
  esac

  case "$basename" in
    test_*.py|*_test.py)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

has_explicit_doc_task_type() {
  local text="$1"

  printf '%s\n' "$text" | grep -Eiq \
    '^[[:space:]#>*-]*(Task Type|Task type|任务类型)[[:space:]]*[:：][[:space:]]*(documentation|doc|document|文档任务|文档)'
}

has_explicit_test_task_type() {
  local text="$1"

  printf '%s\n' "$text" | grep -Eiq \
    '^[[:space:]#>*-]*(Task Type|Task type|任务类型)[[:space:]]*[:：][[:space:]]*(test|tests|testing|测试任务|测试)'
}

is_meta_or_script_task() {
  local text="$1"

  printf '%s\n' "$text" | grep -Eiq \
    '(元任务|meta task|脚本任务|自动化脚本|任务编排器|automation/[[:alnum:]_./-]+\.sh|run_next_task\.sh|run_codex\.sh|validate_codex\.sh|task_queue\.md|current_task\.md|approval\.json)'
}

extract_first_value_from_text() {
  local text="$1"
  shift
  local pattern
  local line
  local value

  for pattern in "$@"; do
    line=$(printf '%s\n' "$text" | grep -Eim1 "$pattern" || true)
    if [ -n "$line" ]; then
      value=$(trim_value "$(printf '%s\n' "$line" | sed -E 's/^[^:：]*[:：][[:space:]]*//')" )
      if [ -n "$value" ] && ! is_placeholder_value "$value"; then
        printf '%s\n' "$value"
        return 0
      fi
    fi
  done

  return 1
}

derive_test_file_from_source() {
  local source_file="$1"
  local base_name

  case "$source_file" in
    *.py)
      ;;
    *)
      return 1
      ;;
  esac

  base_name="$(basename "$source_file" .py)"

  if [ -n "$base_name" ]; then
    printf 'tests/unit/test_%s.py\n' "$base_name"
  fi
}

DOC_FILE=$(
  extract_first_value_from_text "$NEXT_TASK" \
    '^[[:space:]#>*-]*(Regression doc to create|Document file to create|Doc file to create|Target document|Document to update|Documentation file|Doc file|目标文档|文档文件|文档路径)[[:space:]]*[:：]'
) || true

SOURCE_FILE=$(
  extract_first_value_from_text "$NEXT_TASK" \
    '^[[:space:]#>*-]*(Source file to test|Source file|File under test|被测试源码|待测源码|待测文件|源码文件)[[:space:]]*[:：]'
) || true

TEST_FILE=$(
  extract_first_value_from_text "$NEXT_TASK" \
    '^[[:space:]#>*-]*(Test file to create|Test file|Target test file|测试文件|目标测试文件)[[:space:]]*[:：]'
) || true

TASK_TYPE=""
EXPLICIT_TEST_TASK="false"
META_OR_SCRIPT_TASK="false"

if has_explicit_doc_task_type "$NEXT_TASK"; then
  TASK_TYPE="documentation"
fi

if has_explicit_test_task_type "$NEXT_TASK"; then
  EXPLICIT_TEST_TASK="true"
fi

if is_meta_or_script_task "$NEXT_TASK"; then
  META_OR_SCRIPT_TASK="true"
fi

if [ -n "$DOC_FILE" ] && ! is_valid_doc_path "$DOC_FILE"; then
  DOC_FILE=""
fi

if [ -n "$SOURCE_FILE" ] && ! is_valid_source_file_path "$SOURCE_FILE"; then
  SOURCE_FILE=""
fi

if [ -n "$TEST_FILE" ] && ! is_valid_test_file_path "$TEST_FILE"; then
  TEST_FILE=""
fi

if [ -n "$DOC_FILE" ]; then
  TASK_TYPE="documentation"
fi

if [ -z "$TEST_FILE" ] && [ -n "$SOURCE_FILE" ]; then
  TEST_FILE="$(derive_test_file_from_source "$SOURCE_FILE" || true)"
fi

if [ -z "$TASK_TYPE" ] && [ "$EXPLICIT_TEST_TASK" = "true" ]; then
  TASK_TYPE="test"
fi

if [ -z "$TASK_TYPE" ] && [ "$META_OR_SCRIPT_TASK" != "true" ] && { [ -n "$TEST_FILE" ] || [ -n "$SOURCE_FILE" ]; }; then
  TASK_TYPE="test"
fi

mkdir -p "$(dirname "$TASK_FILE")" "$(dirname "$APPROVAL_FILE")" \
  "$(dirname "$RESULT_FILE")" "$(dirname "$VALIDATION_FILE")"

{
  printf "%s\n" "$NEXT_TASK"

  if [ -n "$TASK_TYPE" ]; then
    echo
    echo "## Automation Metadata"

    if [ "$TASK_TYPE" = "documentation" ]; then
      echo "Task Type: documentation"
      if [ -n "$DOC_FILE" ]; then
        echo "Regression doc to create: $DOC_FILE"
        echo "Target document: $DOC_FILE"
      fi
    elif [ "$TASK_TYPE" = "test" ]; then
      echo "Task Type: test"
      if [ -n "$SOURCE_FILE" ]; then
        echo "Source file to test: $SOURCE_FILE"
      fi
      if [ -n "$TEST_FILE" ]; then
        echo "Test file to create: $TEST_FILE"
      fi
    fi
  fi
} > "$TASK_FILE"

echo '{"approved": true}' > "$APPROVAL_FILE"

echo "=== Current Task Written ==="
cat "$TASK_FILE"
echo
echo "=== Running Codex ==="

"$RUN_CODEX_SCRIPT"

echo
echo "=== Codex Result ==="
cat "$RESULT_FILE" 2>/dev/null || true

echo
echo "=== Validation Report ==="
cat "$VALIDATION_FILE" 2>/dev/null || true

if [ -x "$REVIEW_PACKET_SCRIPT" ]; then
  echo
  echo "=== Building Review Packet ==="
  "$REVIEW_PACKET_SCRIPT"
else
  echo
  echo "=== Building Review Packet ==="
  echo "skip: optional script missing or not executable ($REVIEW_PACKET_SCRIPT)"
fi

echo
echo "=== Finished ==="
