#!/usr/bin/env bash
set -euo pipefail

echo "=== 安装 Claude 路由脚本 ==="

mkdir -p ~/.ai-routes

cp ~/Documents/trae_projects/qq/claude-use-anthropic-official.sh ~/.ai-routes/
cp ~/Documents/trae_projects/qq/claude-use-volcengine-ark.sh ~/.ai-routes/
cp ~/Documents/trae_projects/qq/claude-use-deepseek.sh ~/.ai-routes/
cp ~/Documents/trae_projects/qq/claude-use-deepseek-flash.sh ~/.ai-routes/
cp ~/Documents/trae_projects/qq/claude-use-deepseek-flash-full.sh ~/.ai-routes/

chmod +x ~/.ai-routes/claude-use-anthropic-official.sh
chmod +x ~/.ai-routes/claude-use-volcengine-ark.sh
chmod +x ~/.ai-routes/claude-use-deepseek.sh
chmod +x ~/.ai-routes/claude-use-deepseek-flash.sh
chmod +x ~/.ai-routes/claude-use-deepseek-flash-full.sh

echo "路由脚本已安装到 ~/.ai-routes/"
ls -la ~/.ai-routes/claude-use-*.sh
echo ""
echo "下一步: 请执行 source ~/.zshrc 或重启终端"
