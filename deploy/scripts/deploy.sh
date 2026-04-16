#!/bin/bash

# QQ交易机器人部署脚本
# 用于在服务器端接收和部署新版本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置变量
APP_USER="qqbot"
APP_DIR="/opt/qq-bot"
BACKUP_DIR="$APP_DIR/backups"
DEPLOY_DIR="$APP_DIR/deployments"
CURRENT_DIR="$APP_DIR/app"
VENV_PATH="$APP_DIR/.venv"
SERVICE_NAME="qq-bot"

# 参数检查
if [ $# -lt 2 ]; then
    echo "用法: $0 <部署包路径> <环境> [--force]"
    echo "环境: staging | production"
    echo "选项: --force 强制部署（跳过备份）"
    exit 1
fi

DEPLOY_PACKAGE="$1"
ENVIRONMENT="$2"
FORCE_DEPLOY=false

if [ $# -eq 3 ] && [ "$3" = "--force" ]; then
    FORCE_DEPLOY=true
fi

# 验证环境参数
if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    log_error "无效的环境参数: $ENVIRONMENT"
    exit 1
fi

# 验证当前用户
if [ "$(whoami)" != "$APP_USER" ]; then
    log_error "请使用 $APP_USER 用户运行此脚本"
    exit 1
fi

# 验证部署包存在
if [ ! -f "$DEPLOY_PACKAGE" ]; then
    log_error "部署包不存在: $DEPLOY_PACKAGE"
    exit 1
fi

log_info "开始部署QQ交易机器人到 $ENVIRONMENT 环境..."
log_info "部署包: $(basename "$DEPLOY_PACKAGE")"

# 创建部署目录
mkdir -p "$DEPLOY_DIR" "$BACKUP_DIR"

# 1. 备份当前版本
if [ "$FORCE_DEPLOY" = false ]; then
    log_info "备份当前版本..."
    
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    if [ -d "$CURRENT_DIR" ]; then
        tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
            -C "$APP_DIR" \
            app/ \
            scripts/ \
            .env 2>/dev/null || true
        
        if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
            log_success "备份完成: $BACKUP_FILE"
        else
            log_warn "备份创建失败，继续部署..."
        fi
    else
        log_warn "当前版本目录不存在，跳过备份"
    fi
fi

# 2. 停止应用程序服务
log_info "停止应用程序服务..."

if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl stop "$SERVICE_NAME"
    sleep 5
    
    # 确保服务已停止
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_error "无法停止服务 $SERVICE_NAME"
        exit 1
    fi
    
    log_success "服务已停止"
else
    log_warn "服务 $SERVICE_NAME 未运行"
fi

# 3. 解压部署包
log_info "解压部署包..."

# 创建临时目录
TEMP_DIR="$(mktemp -d)"
DEPLOY_VERSION="$(basename "$DEPLOY_PACKAGE" | sed 's/\.tar\.gz$//')"

# 解压到临时目录
tar -xzf "$DEPLOY_PACKAGE" -C "$TEMP_DIR"

# 验证解压结果
if [ ! -d "$TEMP_DIR/app" ]; then
    log_error "部署包格式错误，缺少app目录"
    rm -rf "$TEMP_DIR"
    exit 1
fi

log_success "部署包解压完成"

# 4. 准备新版本
log_info "准备新版本..."

# 备份当前配置和交易数据
if [ -d "$CURRENT_DIR" ]; then
    # 备份配置文件
    if [ -f "$CURRENT_DIR/config.yaml" ]; then
        cp "$CURRENT_DIR/config.yaml" "$TEMP_DIR/app/config.yaml.backup"
    fi
    
    # 备份交易数据
    if [ -f "$CURRENT_DIR/trades.csv" ]; then
        cp "$CURRENT_DIR/trades.csv" "$TEMP_DIR/app/trades.csv.backup"
    fi
    
    # 恢复配置到新版本
    if [ -f "$TEMP_DIR/app/config.yaml.backup" ]; then
        mv "$TEMP_DIR/app/config.yaml.backup" "$TEMP_DIR/app/config.yaml"
        log_success "配置文件已恢复"
    fi
    
    # 恢复交易数据到新版本
    if [ -f "$TEMP_DIR/app/trades.csv.backup" ]; then
        mv "$TEMP_DIR/app/trades.csv.backup" "$TEMP_DIR/app/trades.csv"
        log_success "交易数据已恢复"
    fi
fi

# 5. 部署新版本
log_info "部署新版本..."

# 备份当前版本（如果有）
if [ -d "$CURRENT_DIR" ]; then
    mv "$CURRENT_DIR" "$CURRENT_DIR.old"
fi

# 移动新版本到应用目录
mv "$TEMP_DIR/app" "$CURRENT_DIR"

# 清理临时目录
rm -rf "$TEMP_DIR"

# 6. 安装依赖包
log_info "安装Python依赖包..."

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 检查requirements.txt
if [ -f "$CURRENT_DIR/requirements.txt" ]; then
    pip install -r "$CURRENT_DIR/requirements.txt"
    log_success "依赖包安装完成"
else
    log_warn "未找到requirements.txt，跳过依赖安装"
fi

# 7. 环境配置
log_info "配置环境..."

# 根据环境设置配置
if [ "$ENVIRONMENT" = "production" ]; then
    # 生产环境配置
    if [ -f "$APP_DIR/.env.production" ]; then
        cp "$APP_DIR/.env.production" "$APP_DIR/.env"
        log_success "生产环境配置已应用"
    fi
    
    # 设置生产模式
    export APP_ENV=production
else
    # 测试环境配置
    if [ -f "$APP_DIR/.env.staging" ]; then
        cp "$APP_DIR/.env.staging" "$APP_DIR/.env"
        log_success "测试环境配置已应用"
    fi
    
    # 设置测试模式
    export APP_ENV=staging
fi

# 8. 验证部署
log_info "验证部署..."

# 检查应用程序结构
if [ ! -f "$CURRENT_DIR/main.py" ]; then
    log_error "部署失败：缺少main.py文件"
    # 尝试回滚
    if [ -d "$CURRENT_DIR.old" ]; then
        rm -rf "$CURRENT_DIR"
        mv "$CURRENT_DIR.old" "$CURRENT_DIR"
        log_warn "已回滚到旧版本"
    fi
    exit 1
fi

# 检查Python语法
if ! python -m py_compile "$CURRENT_DIR/main.py"; then
    log_error "Python语法检查失败"
    # 尝试回滚
    if [ -d "$CURRENT_DIR.old" ]; then
        rm -rf "$CURRENT_DIR"
        mv "$CURRENT_DIR.old" "$CURRENT_DIR"
        log_warn "已回滚到旧版本"
    fi
    exit 1
fi

log_success "部署验证通过"

# 9. 启动应用程序
log_info "启动应用程序..."

sudo systemctl start "$SERVICE_NAME"

# 等待服务启动
sleep 10

# 检查服务状态
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_success "应用程序启动成功"
else
    log_error "应用程序启动失败"
    sudo systemctl status "$SERVICE_NAME"
    exit 1
fi

# 10. 清理旧版本
log_info "清理旧版本..."

if [ -d "$CURRENT_DIR.old" ]; then
    # 保留最近3个版本的备份
    find "$APP_DIR" -name "app.old*" -type d | sort -r | tail -n +4 | xargs rm -rf
    
    # 重命名当前备份
    mv "$CURRENT_DIR.old" "$CURRENT_DIR.old.$(date +%Y%m%d_%H%M%S)"
    
    log_success "旧版本清理完成"
fi

# 11. 记录部署历史
log_info "记录部署历史..."

DEPLOY_LOG="$DEPLOY_DIR/deployments.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') | $ENVIRONMENT | $DEPLOY_VERSION | SUCCESS" >> "$DEPLOY_LOG"

# 保留最近100条部署记录
tail -n 100 "$DEPLOY_LOG" > "$DEPLOY_LOG.tmp"
mv "$DEPLOY_LOG.tmp" "$DEPLOY_LOG"

# 12. 完成部署
log_success "QQ交易机器人部署完成！"
log_success "环境: $ENVIRONMENT"
log_success "版本: $DEPLOY_VERSION"
log_success "服务状态: $(systemctl is-active $SERVICE_NAME)"

# 显示后续检查命令
cat << EOF

=== 部署完成 ===

部署信息:
- 环境: $ENVIRONMENT
- 版本: $DEPLOY_VERSION
- 时间: $(date)

检查命令:
- 服务状态: sudo systemctl status $SERVICE_NAME
- 服务日志: sudo journalctl -u $SERVICE_NAME -f
- 应用程序日志: tail -f /var/log/qq-bot/bot.log
- 健康检查: $APP_DIR/scripts/health_check.sh

部署历史: $DEPLOY_LOG
EOF