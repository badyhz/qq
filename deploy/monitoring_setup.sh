#!/bin/bash

# QQ交易机器人监控系统安装脚本

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
LOG_DIR="/var/log/qq-bot"
MONITOR_DIR="$APP_DIR/monitoring"

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
    log_error "请勿使用root用户运行此脚本，使用sudo权限执行特定命令"
    exit 1
fi

log_info "开始安装QQ交易机器人监控系统..."

# 1. 安装系统监控工具
log_info "安装系统监控工具..."

sudo apt update
sudo apt install -y \
    htop \
    iotop \
    nload \
    nethogs \
    dstat \
    sysstat \
    iftop \
    net-tools

# 2. 配置系统监控
log_info "配置系统监控..."

# 启用sysstat（系统性能统计）
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
sudo systemctl enable sysstat
sudo systemctl start sysstat

# 3. 安装应用程序监控
log_info "安装应用程序监控工具..."

# 创建监控目录
sudo -u $APP_USER mkdir -p "$MONITOR_DIR" "$MONITOR_DIR/scripts" "$MONITOR_DIR/alerts"

# 4. 创建健康检查脚本
log_info "创建健康检查脚本..."

sudo -u $APP_USER tee "$MONITOR_DIR/scripts/health_check.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人健康检查脚本

set -e

APP_DIR="/opt/qq-bot"
LOG_DIR="/var/log/qq-bot"
SERVICE_NAME="qq-bot"
ALERT_FILE="$APP_DIR/monitoring/alerts/health_alert.log"

# 初始化健康状态
HEALTH_STATUS="HEALTHY"
ALERT_MESSAGES=()

# 检查服务状态
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    HEALTH_STATUS="CRITICAL"
    ALERT_MESSAGES+=("服务 $SERVICE_NAME 未运行")
fi

# 检查进程是否存在
if ! pgrep -f "python main.py" > /dev/null; then
    HEALTH_STATUS="CRITICAL"
    ALERT_MESSAGES+=("应用程序进程不存在")
fi

# 检查日志文件大小
LOG_FILES=("$LOG_DIR/bot.log" "$LOG_DIR/error.log")
for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        LOG_SIZE=$(du -b "$log_file" 2>/dev/null | cut -f1 || echo 0)
        if [ "$LOG_SIZE" -gt 1073741824 ]; then # 1GB
            ALERT_MESSAGES+=("日志文件过大: $(basename "$log_file") ($((LOG_SIZE/1024/1024))MB)")
            if [ "$HEALTH_STATUS" = "HEALTHY" ]; then
                HEALTH_STATUS="WARNING"
            fi
        fi
    else
        ALERT_MESSAGES+=("日志文件不存在: $(basename "$log_file")")
        if [ "$HEALTH_STATUS" = "HEALTHY" ]; then
            HEALTH_STATUS="WARNING"
        fi
    fi
done

# 检查磁盘空间
DISK_USAGE=$(df "$APP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    HEALTH_STATUS="CRITICAL"
    ALERT_MESSAGES+=("磁盘使用率过高: ${DISK_USAGE}%")
elif [ "$DISK_USAGE" -gt 80 ]; then
    ALERT_MESSAGES+=("磁盘使用率较高: ${DISK_USAGE}%")
    if [ "$HEALTH_STATUS" = "HEALTHY" ]; then
        HEALTH_STATUS="WARNING"
    fi
fi

# 检查内存使用
MEM_USAGE=$(free | awk '/Mem:/ {printf("%.0f", $3/$2 * 100)}')
if [ "$MEM_USAGE" -gt 90 ]; then
    ALERT_MESSAGES+=("内存使用率过高: ${MEM_USAGE}%")
    if [ "$HEALTH_STATUS" = "HEALTHY" ]; then
        HEALTH_STATUS="WARNING"
    fi
fi

# 检查网络连接
NETWORK_HOSTS=("api.binance.com" "stream.binance.com")
for host in "${NETWORK_HOSTS[@]}"; do
    if ! ping -c 1 -W 5 "$host" > /dev/null 2>&1; then
        ALERT_MESSAGES+=("网络连接失败: $host")
        if [ "$HEALTH_STATUS" = "HEALTHY" ]; then
            HEALTH_STATUS="WARNING"
        fi
    fi
done

# 检查交易数据文件
if [ -f "$APP_DIR/app/trades.csv" ]; then
    FILE_AGE=$((($(date +%s) - $(stat -c %Y "$APP_DIR/app/trades.csv")) / 3600))
    if [ "$FILE_AGE" -gt 24 ]; then
        ALERT_MESSAGES+=("交易数据文件超过24小时未更新")
        if [ "$HEALTH_STATUS" = "HEALTHY" ]; then
            HEALTH_STATUS="WARNING"
        fi
    fi
fi

# 输出健康状态
echo "状态: $HEALTH_STATUS"

# 如果有告警信息，记录到告警文件
if [ "${#ALERT_MESSAGES[@]}" -gt 0 ]; then
    echo "$(date): $HEALTH_STATUS - ${ALERT_MESSAGES[*]}" >> "$ALERT_FILE"
    
    # 只显示前5条告警信息
    for i in "${!ALERT_MESSAGES[@]}"; do
        if [ "$i" -lt 5 ]; then
            echo "告警: ${ALERT_MESSAGES[$i]}"
        fi
    done
    
    if [ "${#ALERT_MESSAGES[@]}" -gt 5 ]; then
        echo "... 还有 $(( ${#ALERT_MESSAGES[@]} - 5 )) 条告警"
    fi
fi

# 根据状态返回退出码
case "$HEALTH_STATUS" in
    "HEALTHY") exit 0 ;;
    "WARNING") exit 1 ;;
    "CRITICAL") exit 2 ;;
    *) exit 3 ;;
esac
EOF

sudo chmod +x "$MONITOR_DIR/scripts/health_check.sh"

# 5. 创建性能监控脚本
log_info "创建性能监控脚本..."

sudo -u $APP_USER tee "$MONITOR_DIR/scripts/performance_monitor.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人性能监控脚本

set -e

LOG_DIR="/var/log/qq-bot"
MONITOR_DIR="/opt/qq-bot/monitoring"
METRICS_FILE="$MONITOR_DIR/metrics/performance_metrics.csv"

# 创建指标目录
mkdir -p "$MONITOR_DIR/metrics"

# 如果指标文件不存在，创建表头
if [ ! -f "$METRICS_FILE" ]; then
    echo "timestamp,cpu_usage,memory_usage,disk_usage,network_rx,network_tx,process_count,load_average" > "$METRICS_FILE"
fi

# 获取系统指标
TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEMORY_USAGE=$(free | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')
DISK_USAGE=$(df /opt/qq-bot | tail -1 | awk '{print $5}' | sed 's/%//')

# 获取网络流量（KB/s）
NETWORK_RX=$(cat /proc/net/dev | grep eth0 | awk '{print $2}')
NETWORK_TX=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')

# 获取进程数量
PROCESS_COUNT=$(ps aux | grep -v grep | grep -c qqbot)

# 获取负载平均值
LOAD_AVERAGE=$(cat /proc/loadavg | awk '{print $1}')

# 记录指标
echo "$TIMESTAMP,$CPU_USAGE,$MEMORY_USAGE,$DISK_USAGE,$NETWORK_RX,$NETWORK_TX,$PROCESS_COUNT,$LOAD_AVERAGE" >> "$METRICS_FILE"

# 清理旧数据（保留最近7天）
find "$MONITOR_DIR/metrics" -name "*.csv" -mtime +7 -delete

echo "性能指标记录完成: $TIMESTAMP"
EOF

sudo chmod +x "$MONITOR_DIR/scripts/performance_monitor.sh"

# 6. 创建日志分析脚本
log_info "创建日志分析脚本..."

sudo -u $APP_USER tee "$MONITOR_DIR/scripts/log_analyzer.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人日志分析脚本

set -e

LOG_DIR="/var/log/qq-bot"
MONITOR_DIR="/opt/qq-bot/monitoring"
ANALYSIS_FILE="$MONITOR_DIR/logs/daily_analysis.log"

# 创建日志分析目录
mkdir -p "$MONITOR_DIR/logs"

# 分析今天的日志
TODAY=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/bot.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "日志文件不存在: $LOG_FILE"
    exit 0
fi

# 分析错误日志
ERROR_COUNT=$(grep -c -i "error\|exception\|fail" "$LOG_FILE" 2>/dev/null || echo 0)
WARNING_COUNT=$(grep -c -i "warn" "$LOG_FILE" 2>/dev/null || echo 0)

# 分析交易活动
TRADE_COUNT=$(grep -c "TRADE_EXECUTED" "$LOG_FILE" 2>/dev/null || echo 0)
SIGNAL_COUNT=$(grep -c "SIGNAL_GENERATED" "$LOG_FILE" 2>/dev/null || echo 0)

# 分析网络连接
RECONNECT_COUNT=$(grep -c "reconnect\|disconnect" "$LOG_FILE" 2>/dev/null || echo 0)

# 记录分析结果
{
    echo "=== 日志分析报告 ($TODAY) ==="
    echo "分析时间: $(date)"
    echo "日志文件: $LOG_FILE"
    echo ""
    echo "错误统计:"
    echo "  错误数量: $ERROR_COUNT"
    echo "  警告数量: $WARNING_COUNT"
    echo ""
    echo "交易统计:"
    echo "  交易执行: $TRADE_COUNT"
    echo "  信号生成: $SIGNAL_COUNT"
    echo ""
    echo "网络统计:"
    echo "  重连次数: $RECONNECT_COUNT"
    echo ""
    echo "最近错误:"
    grep -i "error\|exception" "$LOG_FILE" | tail -5 | while read line; do
        echo "  $line"
    done
    echo ""
    echo "=== 分析完成 ==="
} >> "$ANALYSIS_FILE"

# 保留最近30天的分析报告
find "$MONITOR_DIR/logs" -name "daily_analysis.log" -mtime +30 -delete

echo "日志分析完成: $TODAY"
EOF

sudo chmod +x "$MONITOR_DIR/scripts/log_analyzer.sh"

# 7. 安装和配置Prometheus Node Exporter（可选）
log_info "安装Prometheus Node Exporter..."

# 下载并安装Node Exporter
NODE_EXPORTER_VERSION="1.7.0"
wget -q "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar -xzf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
sudo mv "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /usr/local/bin/
sudo chmod +x /usr/local/bin/node_exporter

# 创建系统服务
sudo tee /etc/systemd/system/node_exporter.service > /dev/null << EOF
[Unit]
Description=Prometheus Node Exporter
After=network.target

[Service]
Type=simple
User=qqbot
Group=qqbot
ExecStart=/usr/local/bin/node_exporter
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter

# 8. 配置监控定时任务
log_info "配置监控定时任务..."

# 创建监控crontab
sudo -u $APP_USER tee /tmp/monitor_cron > /dev/null << EOF
# 每分钟检查健康状态
* * * * * $MONITOR_DIR/scripts/health_check.sh > /dev/null 2>&1

# 每5分钟记录性能指标
*/5 * * * * $MONITOR_DIR/scripts/performance_monitor.sh > /dev/null 2>&1

# 每天凌晨1点分析日志
0 1 * * * $MONITOR_DIR/scripts/log_analyzer.sh > /dev/null 2>&1

# 每周清理旧数据
0 2 * * 0 find $MONITOR_DIR -name "*.log" -mtime +30 -delete
EOF

sudo -u $APP_USER crontab /tmp/monitor_cron
rm /tmp/monitor_cron

# 9. 创建监控仪表板脚本
log_info "创建监控仪表板脚本..."

sudo -u $APP_USER tee "$MONITOR_DIR/scripts/dashboard.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人监控仪表板

clear
echo "=== QQ交易机器人监控仪表板 ==="
echo "更新时间: $(date)"
echo ""

# 系统信息
echo "系统信息:"
echo "  主机名: $(hostname)"
echo "  运行时间: $(uptime -p)"
echo "  负载: $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
echo ""

# 服务状态
echo "服务状态:"
if systemctl is-active --quiet qq-bot; then
    echo "  QQ交易机器人: ✅ 运行中"
    SERVICE_STATUS=$(systemctl status qq-bot | grep "Active:" | cut -d':' -f2-)
    echo "  状态: $SERVICE_STATUS"
else
    echo "  QQ交易机器人: ❌ 未运行"
fi

if systemctl is-active --quiet node_exporter; then
    echo "  Node Exporter: ✅ 运行中"
else
    echo "  Node Exporter: ❌ 未运行"
fi
echo ""

# 资源使用
echo "资源使用:"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEMORY_USAGE=$(free | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')
DISK_USAGE=$(df /opt/qq-bot | tail -1 | awk '{print $5}')

echo "  CPU使用率: $CPU_USAGE%"
echo "  内存使用率: $MEMORY_USAGE%"
echo "  磁盘使用率: $DISK_USAGE"
echo ""

# 网络状态
echo "网络状态:"
if ping -c 1 -W 3 api.binance.com > /dev/null 2>&1; then
    echo "  Binance API: ✅ 可连接"
else
    echo "  Binance API: ❌ 不可连接"
fi

if ping -c 1 -W 3 stream.binance.com > /dev/null 2>&1; then
    echo "  Binance Stream: ✅ 可连接"
else
    echo "  Binance Stream: ❌ 不可连接"
fi
echo ""

# 交易统计
echo "交易统计:"
if [ -f "/opt/qq-bot/app/trades.csv" ]; then
    TRADE_COUNT=$(wc -l < /opt/qq-bot/app/trades.csv)
    echo "  总交易次数: $((TRADE_COUNT - 1))"  # 减去表头
    
    if [ "$TRADE_COUNT" -gt 1 ]; then
        LAST_TRADE=$(tail -n 1 /opt/qq-bot/app/trades.csv)
        echo "  最新交易: $LAST_TRADE"
    fi
else
    echo "  交易文件不存在"
fi
echo ""

# 最近告警
echo "最近告警:"
ALERT_FILE="/opt/qq-bot/monitoring/alerts/health_alert.log"
if [ -f "$ALERT_FILE" ] && [ -s "$ALERT_FILE" ]; then
    tail -n 3 "$ALERT_FILE" | while read alert; do
        echo "  $alert"
    done
else
    echo "  无告警"
fi
echo ""

echo "=== 仪表板结束 ==="
EOF

sudo chmod +x "$MONITOR_DIR/scripts/dashboard.sh"

# 10. 创建告警通知脚本
log_info "创建告警通知脚本..."

sudo -u $APP_USER tee "$MONITOR_DIR/scripts/alert_notifier.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人告警通知脚本

set -e

ALERT_FILE="/opt/qq-bot/monitoring/alerts/health_alert.log"
LAST_ALERT_FILE="/opt/qq-bot/monitoring/alerts/last_alert.txt"

# 检查是否有新告警
if [ ! -f "$ALERT_FILE" ]; then
    exit 0
fi

# 获取最新告警
CURRENT_ALERT=$(tail -n 1 "$ALERT_FILE")

# 检查是否与上次告警相同
if [ -f "$LAST_ALERT_FILE" ]; then
    LAST_ALERT=$(cat "$LAST_ALERT_FILE")
    if [ "$CURRENT_ALERT" = "$LAST_ALERT" ]; then
        # 相同告警，不重复通知
        exit 0
    fi
fi

# 记录当前告警
echo "$CURRENT_ALERT" > "$LAST_ALERT_FILE"

# 发送通知（这里可以集成邮件、短信、Webhook等）
echo "新告警: $CURRENT_ALERT"

# 示例：发送到系统日志
logger -t qqbot-alert "$CURRENT_ALERT"

# 示例：发送到Slack（需要配置webhook）
# if [ -n "$SLACK_WEBHOOK" ]; then
#     curl -X POST -H 'Content-type: application/json' \
#          --data "{\"text\":\"QQ交易机器人告警: $CURRENT_ALERT\"}" \
#          "$SLACK_WEBHOOK"
# fi

echo "告警通知已发送"
EOF

sudo chmod +x "$MONITOR_DIR/scripts/alert_notifier.sh"

log_success "监控系统安装完成！"

# 显示监控系统信息
cat << EOF

=== 监控系统配置完成 ===

监控组件:
✅ 系统监控工具 (htop, iotop, nload等)
✅ 健康检查脚本
✅ 性能监控脚本
✅ 日志分析脚本
✅ Prometheus Node Exporter
✅ 监控仪表板
✅ 告警通知系统

重要文件位置:
- 监控脚本: $MONITOR_DIR/scripts/
- 性能指标: $MONITOR_DIR/metrics/
- 分析报告: $MONITOR_DIR/logs/
- 告警记录: $MONITOR_DIR/alerts/

使用命令:
- 查看仪表板: $MONITOR_DIR/scripts/dashboard.sh
- 健康检查: $MONITOR_DIR/scripts/health_check.sh
- 性能监控: $MONITOR_DIR/scripts/performance_monitor.sh

定时任务已配置:
- 每分钟健康检查
- 每5分钟性能记录
- 每日日志分析

下一步:
1. 配置告警通知渠道（邮件、Slack等）
2. 设置外部监控系统（如Prometheus + Grafana）
3. 配置日志聚合系统（如ELK Stack）
EOF