#!/usr/bin/env bash
set -euo pipefail

echo "=== 安装 Claude 路由脚本 ==="

mkdir -p ~/.ai-routes

shopt -s nullglob
ROUTE_SCRIPTS=(~/Documents/trae_projects/qq/claude-use-*.sh)
if [ "${#ROUTE_SCRIPTS[@]}" -eq 0 ]; then
  echo "ERROR: no route scripts found"
  exit 1
fi

cp "${ROUTE_SCRIPTS[@]}" ~/.ai-routes/
chmod +x ~/.ai-routes/claude-use-*.sh

echo "路由脚本已安装到 ~/.ai-routes/"
ls -la ~/.ai-routes/claude-use-*.sh
echo ""
echo "下一步: 请执行 source ~/.zshrc 或重启终端"
