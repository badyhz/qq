# ===== 安装脚本: 部署 Claude 路由快捷命令 =====
# 用法: bash ~/Documents/trae_projects/qq/deploy-routes.sh

echo "=== 1. 复制路由脚本到 ~/.ai-routes/ ==="
mkdir -p ~/.ai-routes
cp ~/Documents/trae_projects/qq/claude-use-anthropic-official.sh ~/.ai-routes/
cp ~/Documents/trae_projects/qq/claude-use-volcengine-ark.sh ~/.ai-routes/
cp ~/Documents/trae_projects/qq/claude-use-deepseek.sh ~/.ai-routes/
chmod +x ~/.ai-routes/claude-use-*.sh
echo "  OK"

echo ""
echo "=== 2. 备份 ~/.zshrc ==="
TS=$(date +%Y%m%d_%H%M%S)
cp -n ~/.zshrc ~/.zshrc.bak."$TS" 2>/dev/null && echo "  backup: ~/.zshrc.bak.$TS" || echo "  backup skipped (already exists?)"

echo ""
echo "=== 3. 追加快捷命令到 ~/.zshrc ==="

read -r -d '' BLOCK << 'ZSHBLOCK'

# BEGIN CLAUDE_ROUTE_SWITCHERS
cc-official() {
  cd ~/Documents/trae_projects/qq || return 1
  source ~/.ai-routes/claude-use-anthropic-official.sh
  claude "$@"
}

cc-ark() {
  cd ~/Documents/trae_projects/qq || return 1
  source ~/.ai-routes/claude-use-volcengine-ark.sh
  claude "$@"
}

cc-deep() {
  cd ~/Documents/trae_projects/qq || return 1
  source ~/.ai-routes/claude-use-deepseek.sh
  claude "$@"
}

cc-test-official() {
  cd ~/Documents/trae_projects/qq || return 1
  source ~/.ai-routes/claude-use-anthropic-official.sh
  claude -p "请只回复 OK"
}

cc-test-ark() {
  cd ~/Documents/trae_projects/qq || return 1
  source ~/.ai-routes/claude-use-volcengine-ark.sh
  claude -p "请只回复 OK"
}

cc-test-deep() {
  cd ~/Documents/trae_projects/qq || return 1
  source ~/.ai-routes/claude-use-deepseek.sh
  claude -p "请只回复 OK"
}

cc-route() {
  echo "Claude route env:"
  echo "ANTHROPIC_BASE_URL=\${ANTHROPIC_BASE_URL:-<unset>}"
  echo "ANTHROPIC_AUTH_TOKEN=\${ANTHROPIC_AUTH_TOKEN:+<set>}"
  echo "ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY:+<set>}"
  echo "ANTHROPIC_MODEL=\${ANTHROPIC_MODEL:-<unset>}"
  echo "ANTHROPIC_DEFAULT_OPUS_MODEL=\${ANTHROPIC_DEFAULT_OPUS_MODEL:-<unset>}"
  echo "ANTHROPIC_DEFAULT_SONNET_MODEL=\${ANTHROPIC_DEFAULT_SONNET_MODEL:-<unset>}"
  echo "ANTHROPIC_DEFAULT_HAIKU_MODEL=\${ANTHROPIC_DEFAULT_HAIKU_MODEL:-<unset>}"
  echo "ANTHROPIC_SMALL_FAST_MODEL=\${ANTHROPIC_SMALL_FAST_MODEL:-<unset>}"
  echo "CLAUDE_CODE_SUBAGENT_MODEL=\${CLAUDE_CODE_SUBAGENT_MODEL:-<unset>}"
  echo "CLAUDE_CODE_USE_VERTEX=\${CLAUDE_CODE_USE_VERTEX:-<unset>}"
  echo "CLAUDE_CODE_USE_BEDROCK=\${CLAUDE_CODE_USE_BEDROCK:-<unset>}"
}
# END CLAUDE_ROUTE_SWITCHERS
ZSHBLOCK

# Check if block already exists
if grep -q "BEGIN CLAUDE_ROUTE_SWITCHERS" ~/.zshrc; then
  echo "  WARNING: Block already exists in ~/.zshrc, skipping. Remove manually if you want to re-add."
else
  echo "$BLOCK" >> ~/.zshrc
  echo "  Appended to ~/.zshrc"
fi

echo ""
echo "=== 4. 生效 ==="
source ~/.zshrc 2>/dev/null && echo "  source ~/.zshrc OK (in this shell)" || echo "  (source in current shell skipped - run manually: source ~/.zshrc)"

echo ""
echo "=== 部署完成 ==="
echo "可用命令:"
echo "  cc-official     - 使用 Anthropic 官方 API 运行 Claude Code"
echo "  cc-ark          - 使用火山 Ark Coding API 运行 Claude Code"
echo "  cc-deep         - 使用 DeepSeek API 运行 Claude Code"
echo "  cc-test-official- 测试 Anthropic 官方路由"
echo "  cc-test-ark     - 测试火山 Ark 路由"
echo "  cc-test-deep    - 测试 DeepSeek 路由"
echo "  cc-route        - 查看当前路由环境变量"
