#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$HOME/Documents/trae_projects/qq"
ROUTE_DIR="$HOME/.ai-routes"
ZSHRC="$HOME/.zshrc"
BEGIN_MARKER="# BEGIN CLAUDE_ROUTE_SWITCHERS"
END_MARKER="# END CLAUDE_ROUTE_SWITCHERS"

mkdir -p "$ROUTE_DIR"

echo "=== 1. 复制路由脚本到 ~/.ai-routes/ ==="
shopt -s nullglob
ROUTE_SCRIPTS=("$PROJECT_DIR"/claude-use-*.sh)
if [ "${#ROUTE_SCRIPTS[@]}" -eq 0 ]; then
  echo "ERROR: no route scripts found under $PROJECT_DIR"
  exit 1
fi
cp "${ROUTE_SCRIPTS[@]}" "$ROUTE_DIR"/
chmod +x "$ROUTE_DIR"/claude-use-*.sh
echo "  OK"

echo ""
echo "=== 2. 备份 ~/.zshrc ==="
TS=$(date +%Y%m%d_%H%M%S)
cp -n "$ZSHRC" "$HOME/.zshrc.bak.$TS" 2>/dev/null && echo "  backup: ~/.zshrc.bak.$TS" || echo "  backup skipped (already exists?)"

echo ""
echo "=== 3. 更新快捷命令 managed block 到 ~/.zshrc ==="

read -r -d '' BLOCK << 'ZSHBLOCK' || true
# BEGIN CLAUDE_ROUTE_SWITCHERS
if [[ ":$PATH:" != *":$HOME/.ai-routes:"* ]]; then
  export PATH="$HOME/.ai-routes:$PATH"
fi

_cc_route_project_dir="$HOME/Documents/trae_projects/qq"
_cc_route_dir="$HOME/.ai-routes"

_cc_route_wrap() {
  local script="$1"
  local fn_name="$2"
  eval "${fn_name}() { cd \"\$_cc_route_project_dir\" || return 1; \"${script}\" \"\$@\"; }"
}

_cc_route_wrap_test() {
  local script="$1"
  local fn_name="$2"
  eval "${fn_name}() { cd \"\$_cc_route_project_dir\" || return 1; \"${script}\" -p \"请只回复 OK\"; }"
}

_cc_route_register_dynamic() {
  local script base route fn test_fn
  for script in "$_cc_route_dir"/claude-use-*.sh; do
    [[ -x "$script" ]] || continue
    base="${script##*/}"
    route="${base#claude-use-}"
    route="${route%.sh}"
    fn="cc-${route}"
    test_fn="cc-test-${route}"
    _cc_route_wrap "$script" "$fn"
    _cc_route_wrap_test "$script" "$test_fn"
  done
}

_cc_route_register_compat_aliases() {
  if typeset -f cc-anthropic-official >/dev/null 2>&1; then
    cc-official() { cc-anthropic-official "$@"; }
    cc-test-official() { cc-test-anthropic-official "$@"; }
  fi
  if typeset -f cc-volcengine-ark >/dev/null 2>&1; then
    cc-ark() { cc-volcengine-ark "$@"; }
    cc-test-ark() { cc-test-volcengine-ark "$@"; }
  fi
  if typeset -f cc-deepseek >/dev/null 2>&1; then
    cc-deep() { cc-deepseek "$@"; }
    cc-deep-pro() { cc-deepseek "$@"; }
    cc-test-deep() { cc-test-deepseek "$@"; }
    cc-test-deep-pro() { cc-test-deepseek "$@"; }
  fi
  if typeset -f cc-deepseek-flash >/dev/null 2>&1; then
    cc-deep-flash() { cc-deepseek-flash "$@"; }
    cc-test-deep-flash() { cc-test-deepseek-flash "$@"; }
  fi
  if typeset -f cc-deepseek-flash-full >/dev/null 2>&1; then
    cc-deep-flash-full() { cc-deepseek-flash-full "$@"; }
    cc-deep-flash-bypass() { cc-deepseek-flash-full "$@"; }
    cc-deep-flash-unsafe() { cc-deepseek-flash-full "$@"; }
    cc-test-deep-flash-full() { cc-test-deepseek-flash-full "$@"; }
  fi
}

_cc_route_register_dynamic
_cc_route_register_compat_aliases

cc-route() {
  echo "Claude route env:"
  echo "ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-<unset>}"
  echo "ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN:+<set>}"
  echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+<set>}"
  echo "ANTHROPIC_MODEL=${ANTHROPIC_MODEL:-<unset>}"
  echo "ANTHROPIC_DEFAULT_OPUS_MODEL=${ANTHROPIC_DEFAULT_OPUS_MODEL:-<unset>}"
  echo "ANTHROPIC_DEFAULT_SONNET_MODEL=${ANTHROPIC_DEFAULT_SONNET_MODEL:-<unset>}"
  echo "ANTHROPIC_DEFAULT_HAIKU_MODEL=${ANTHROPIC_DEFAULT_HAIKU_MODEL:-<unset>}"
  echo "ANTHROPIC_SMALL_FAST_MODEL=${ANTHROPIC_SMALL_FAST_MODEL:-<unset>}"
  echo "CLAUDE_CODE_SUBAGENT_MODEL=${CLAUDE_CODE_SUBAGENT_MODEL:-<unset>}"
  echo "CLAUDE_CODE_USE_VERTEX=${CLAUDE_CODE_USE_VERTEX:-<unset>}"
  echo "CLAUDE_CODE_USE_BEDROCK=${CLAUDE_CODE_USE_BEDROCK:-<unset>}"
  echo "MIMO_API_KEY=${MIMO_API_KEY:+<set>}"
  echo "MIMO_BASE_URL=${MIMO_BASE_URL:-<unset>}"
}
# END CLAUDE_ROUTE_SWITCHERS
ZSHBLOCK

if [ ! -f "$ZSHRC" ]; then
  touch "$ZSHRC"
fi

BLOCK_FILE="$ZSHRC.claude_routes.block"
printf "%s\n" "$BLOCK" > "$BLOCK_FILE"

if grep -qF "$BEGIN_MARKER" "$ZSHRC"; then
  awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" -v block_file="$BLOCK_FILE" '
    function print_block(  line) {
      while ((getline line < block_file) > 0) {
        print line
      }
      close(block_file)
    }
    BEGIN { in_block = 0; replaced = 0 }
    index($0, begin) {
      if (!replaced) {
        print_block()
        replaced = 1
      }
      in_block = 1
      next
    }
    index($0, end) {
      in_block = 0
      next
    }
    !in_block { print }
    END {
      if (!replaced) {
        print_block()
      }
    }
  ' "$ZSHRC" > "$ZSHRC.tmp"
  mv "$ZSHRC.tmp" "$ZSHRC"
  echo "  Managed block replaced"
else
  printf "\n%s\n" "$BLOCK" >> "$ZSHRC"
  echo "  Managed block appended"
fi
rm -f "$BLOCK_FILE"

echo ""
echo "=== 4. 生效 ==="
# shellcheck disable=SC1090
source "$ZSHRC" 2>/dev/null && echo "  source ~/.zshrc OK (in this shell)" || echo "  (source in current shell skipped - run manually: source ~/.zshrc)"

echo ""
echo "=== 部署完成 ==="
echo "可用命令(动态发现 + 兼容别名):"
for script in "$ROUTE_DIR"/claude-use-*.sh; do
  [ -x "$script" ] || continue
  base="${script##*/}"
  route="${base#claude-use-}"
  route="${route%.sh}"
  echo "  cc-$route"
  echo "  cc-test-$route"
done
echo "  cc-official / cc-ark / cc-deep / cc-deep-pro / cc-deep-flash / cc-deep-flash-full"
echo "  cc-deep-flash-bypass / cc-deep-flash-unsafe / cc-route"
