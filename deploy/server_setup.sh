#!/bin/bash

# QQ交易机器人服务器环境配置脚本
# 适用于Ubuntu 22.04 LTS

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
    log_error "请勿使用root用户运行此脚本，使用sudo权限执行特定命令"
    exit 1
fi

# 配置变量
APP_USER="qqbot"
APP_DIR="/opt/qq-bot"
LOG_DIR="/var/log/qq-bot"
BACKUP_DIR="/opt/qq-bot/backups"

log_info "开始配置QQ交易机器人服务器环境..."

# 1. 系统更新和基础包安装
log_info "更新系统包管理器..."
sudo apt update
sudo apt upgrade -y

log_info "安装基础工具包..."
sudo apt install -y \
    curl wget vim git htop nload \
    build-essential libssl-dev libffi-dev \
    python3.11 python3.11-venv python3.11-dev \
    ufw fail2ban logrotate

# 2. 创建应用程序用户和目录
log_info "创建应用程序用户和目录结构..."
sudo useradd -r -s /bin/false -d $APP_DIR $APP_USER
sudo mkdir -p $APP_DIR $LOG_DIR $BACKUP_DIR
sudo chown $APP_USER:$APP_USER $APP_DIR $LOG_DIR $BACKUP_DIR
sudo chmod 755 $APP_DIR $LOG_DIR $BACKUP_DIR

# 3. 配置时区
log_info "配置系统时区..."
sudo timedatectl set-timezone Asia/Shanghai

# 4. 系统参数优化
log_info "优化系统内核参数..."
sudo tee -a /etc/sysctl.conf > /dev/null << EOF
# 网络优化参数
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# 内存优化参数
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF

sudo sysctl -p

# 5. 配置防火墙
log_info "配置防火墙规则..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH连接（默认端口22）
sudo ufw allow ssh

# 允许HTTPS（如果需要Web界面）
sudo ufw allow 443/tcp

# 允许自定义应用程序端口（如果需要）
# sudo ufw allow 8080/tcp

sudo ufw --force reload

# 6. 配置fail2ban
log_info "配置fail2ban防护..."
sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
[DEFAULT]
# 禁止时间（秒）
bantime = 3600

# 查找时间窗口（秒）
findtime = 600

# 最大失败次数
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

# 如果需要保护其他服务，可以添加更多配置
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 7. 配置日志轮转
log_info "配置应用程序日志轮转..."
sudo tee /etc/logrotate.d/qq-bot > /dev/null << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 644 $APP_USER $APP_USER
}
EOF

# 8. 创建Python虚拟环境
log_info "创建Python虚拟环境..."
sudo -u $APP_USER python3.11 -m venv $APP_DIR/.venv

# 9. 配置环境变量
log_info "配置应用程序环境变量..."
sudo -u $APP_USER tee $APP_DIR/.env > /dev/null << EOF
# QQ交易机器人环境配置
APP_ENV=production
PYTHONPATH=$APP_DIR/app

# 交易配置（生产环境需要设置真实值）
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# 应用程序配置
QQ_CONFIG_PATH=$APP_DIR/app/config.yaml
QQ_LOOP_INTERVAL_SECONDS=0.5
QQ_HEARTBEAT_INTERVAL_SECONDS=60

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=$LOG_DIR/bot.log
ERROR_LOG_FILE=$LOG_DIR/error.log
DETAILED_LOG_FILE=$LOG_DIR/detailed.log
EOF

sudo chmod 600 $APP_DIR/.env

# 10. 创建启动脚本
log_info "创建应用程序启动脚本..."
sudo -u $APP_USER tee $APP_DIR/start.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人启动脚本

set -e

APP_DIR=$(dirname "$(readlink -f "$0")")
VENV_PATH="$APP_DIR/.venv"
APP_PATH="$APP_DIR/app"

# 加载环境变量
if [ -f "$APP_DIR/.env" ]; then
    export $(grep -v '^#' "$APP_DIR/.env" | xargs)
fi

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 设置Python路径
export PYTHONPATH="$APP_PATH:$PYTHONPATH"

# 启动应用程序
cd "$APP_PATH"
python main.py
EOF

sudo chmod +x $APP_DIR/start.sh

# 11. 创建系统服务
log_info "创建系统服务配置..."
sudo tee /etc/systemd/system/qq-bot.service > /dev/null << EOF
[Unit]
Description=QQ Trading Bot
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/app
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/start.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

# 12. 配置备份脚本
log_info "创建数据备份脚本..."
sudo -u $APP_USER tee $APP_DIR/backup.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人数据备份脚本

set -e

BACKUP_DIR="/opt/qq-bot/backups"
APP_DIR="/opt/qq-bot/app"
LOG_DIR="/var/log/qq-bot"
BACKUP_FILE="qq-bot-backup-$(date +%Y%m%d_%H%M%S).tar.gz"

# 创建备份
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    "$APP_DIR/config.yaml" \
    "$APP_DIR/trades.csv" \
    "$LOG_DIR" 2>/dev/null || true

# 清理30天前的备份
find "$BACKUP_DIR" -name "qq-bot-backup-*.tar.gz" -mtime +30 -delete

echo "备份完成: $BACKUP_FILE"
EOF

sudo chmod +x $APP_DIR/backup.sh

# 13. 配置定时备份
log_info "配置定时备份任务..."
sudo -u $APP_USER tee /tmp/cron_backup > /dev/null << EOF
# 每天凌晨2点执行备份
0 2 * * * $APP_DIR/backup.sh > /dev/null 2>&1

# 每周日凌晨3点清理日志
0 3 * * 0 find $LOG_DIR -name "*.log.*" -mtime +7 -delete
EOF

sudo -u $APP_USER crontab /tmp/cron_backup
rm /tmp/cron_backup

# 14. 创建健康检查脚本
log_info "创建健康检查脚本..."
sudo -u $APP_USER tee $APP_DIR/health_check.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人健康检查脚本

set -e

APP_DIR="/opt/qq-bot"
LOG_DIR="/var/log/qq-bot"
SERVICE_NAME="qq-bot"

# 检查服务状态
if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "ERROR: 服务 $SERVICE_NAME 未运行"
    exit 1
fi

# 检查日志文件大小
LOG_SIZE=$(du -b "$LOG_DIR/bot.log" 2>/dev/null | cut -f1 || echo 0)
if [ "$LOG_SIZE" -gt 1073741824 ]; then # 1GB
    echo "WARN: 日志文件过大 ($LOG_SIZE bytes)"
fi

# 检查磁盘空间
DISK_USAGE=$(df "$APP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "WARN: 磁盘使用率过高 ($DISK_USAGE%)"
fi

# 检查网络连接
if ! ping -c 1 -W 5 api.binance.com > /dev/null 2>&1; then
    echo "WARN: 无法连接到交易所API"
fi

echo "OK: 系统运行正常"
EOF

sudo chmod +x $APP_DIR/health_check.sh

log_info "服务器环境配置完成！"

# 显示后续步骤
cat << EOF

=== 部署完成提示 ===

1. 服务器基础环境已配置完成
2. 接下来需要：
   - 上传应用程序代码到 $APP_DIR/app/
   - 配置生产环境参数（API密钥等）
   - 安装Python依赖包
   - 启动系统服务

3. 重要文件位置：
   - 应用程序目录: $APP_DIR/app/
   - 日志目录: $LOG_DIR/
   - 配置文件: $APP_DIR/.env
   - 系统服务: /etc/systemd/system/qq-bot.service

4. 常用命令：
   - 启动服务: sudo systemctl start qq-bot
   - 停止服务: sudo systemctl stop qq-bot
   - 查看状态: sudo systemctl status qq-bot
   - 查看日志: sudo journalctl -u qq-bot -f

请按照上述步骤完成应用程序部署。
EOF