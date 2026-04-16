# QQ交易机器人部署验证和性能测试指南

## 1. 部署验证流程

### 1.1 环境验证脚本

```bash
sudo -u qqbot tee /opt/qq-bot/scripts/validate_deployment.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人部署验证脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }

echo "=== QQ交易机器人部署验证 ==="
echo "验证时间: $(date)"
echo ""

# 1. 系统环境验证
log_info "1. 系统环境验证..."

# 检查操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_success "操作系统: $PRETTY_NAME"
else
    log_error "无法确定操作系统"
fi

# 检查Python版本
PYTHON_VERSION=$(python3.11 --version 2>/dev/null | cut -d' ' -f2)
if [ -n "$PYTHON_VERSION" ]; then
    log_success "Python版本: $PYTHON_VERSION"
else
    log_error "Python 3.11未安装"
fi

# 检查虚拟环境
if [ -d "/opt/qq-bot/.venv" ]; then
    log_success "虚拟环境存在"
else
    log_error "虚拟环境不存在"
fi

echo ""

# 2. 应用程序结构验证
log_info "2. 应用程序结构验证..."

APP_DIR="/opt/qq-bot/app"
REQUIRED_FILES=("main.py" "config.yaml" "core/" "utils/")

for file in "${REQUIRED_FILES[@]}"; do
    if [ -e "$APP_DIR/$file" ]; then
        log_success "文件存在: $file"
    else
        log_error "文件缺失: $file"
    fi
done

echo ""

# 3. 服务状态验证
log_info "3. 服务状态验证..."

SERVICE_NAME="qq-bot"

if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_success "服务运行状态: 活跃"
    
    # 检查服务详情
    SERVICE_STATUS=$(systemctl status "$SERVICE_NAME" | grep "Active:" | cut -d':' -f2-)
    log_info "服务详情: $SERVICE_STATUS"
    
    # 检查进程
    if pgrep -f "python main.py" > /dev/null; then
        log_success "应用程序进程运行中"
    else
        log_error "应用程序进程未运行"
    fi
else
    log_error "服务未运行"
fi

echo ""

# 4. 网络连接验证
log_info "4. 网络连接验证..."

# 检查交易所API连接
API_HOSTS=("api.binance.com" "stream.binance.com")

for host in "${API_HOSTS[@]}"; do
    if ping -c 1 -W 3 "$host" > /dev/null 2>&1; then
        log_success "网络可达: $host"
    else
        log_error "网络不可达: $host"
    fi
done

# 检查端口连接
if nc -z api.binance.com 443 2>/dev/null; then
    log_success "HTTPS端口(443)可连接"
else
    log_error "HTTPS端口(443)连接失败"
fi

echo ""

# 5. 数据存储验证
log_info "5. 数据存储验证..."

# 检查数据目录
DATA_DIRS=("/opt/qq-bot/data" "/var/log/qq-bot")

for dir in "${DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        PERMISSIONS=$(stat -c "%a %U:%G" "$dir")
        log_success "目录存在: $dir ($PERMISSIONS)"
    else
        log_error "目录不存在: $dir"
    fi
done

# 检查日志文件
LOG_FILES=("/var/log/qq-bot/bot.log" "/var/log/qq-bot/error.log")

for file in "${LOG_FILES[@]}"; do
    if [ -f "$file" ]; then
        SIZE=$(du -h "$file" | cut -f1)
        log_success "日志文件: $(basename "$file") ($SIZE)"
    else
        log_warn "日志文件不存在: $(basename "$file")"
    fi
done

echo ""

# 6. 配置验证
log_info "6. 配置验证..."

# 检查环境变量
if [ -f "/opt/qq-bot/.env" ]; then
    log_success "环境变量文件存在"
    
    # 检查关键配置
    if grep -q "APP_ENV" /opt/qq-bot/.env; then
        APP_ENV=$(grep "APP_ENV" /opt/qq-bot/.env | cut -d'=' -f2)
        log_success "应用程序环境: $APP_ENV"
    else
        log_warn "未设置APP_ENV"
    fi
else
    log_error "环境变量文件不存在"
fi

# 检查配置文件
if [ -f "$APP_DIR/config.yaml" ]; then
    if python3 -c "import yaml; yaml.safe_load(open('$APP_DIR/config.yaml'))" 2>/dev/null; then
        log_success "配置文件语法正确"
    else
        log_error "配置文件语法错误"
    fi
else
    log_error "配置文件不存在"
fi

echo ""

# 7. 功能测试
log_info "7. 功能测试..."

# 测试Python导入
if python3 -c "import sys; sys.path.append('$APP_DIR'); from main import TradingApplication; print('导入成功')" 2>/dev/null; then
    log_success "Python模块导入正常"
else
    log_error "Python模块导入失败"
fi

# 测试依赖包
REQUIRED_PACKAGES=("numpy" "pandas" "websocket" "binance" "ccxt")

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $pkg; print('$pkg OK')" 2>/dev/null; then
        log_success "依赖包: $pkg"
    else
        log_error "依赖包缺失: $pkg"
    fi
done

echo ""

# 8. 性能基准测试
log_info "8. 性能基准测试..."

# 内存使用测试
MEMORY_USAGE=$(free -m | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')
if (( $(echo "$MEMORY_USAGE < 80" | bc -l) )); then
    log_success "内存使用率: ${MEMORY_USAGE}%"
else
    log_warn "内存使用率较高: ${MEMORY_USAGE}%"
fi

# CPU使用测试
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
if (( $(echo "$CPU_USAGE < 70" | bc -l) )); then
    log_success "CPU使用率: ${CPU_USAGE}%"
else
    log_warn "CPU使用率较高: ${CPU_USAGE}%"
fi

# 磁盘I/O测试
DISK_IO=$(iostat -d 1 1 | grep -v "^$" | tail -1 | awk '{print $2}')
if (( $(echo "$DISK_IO < 100" | bc -l) )); then
    log_success "磁盘I/O: ${DISK_IO} tps"
else
    log_warn "磁盘I/O较高: ${DISK_IO} tps"
fi

echo ""

# 9. 安全验证
log_info "9. 安全验证..."

# 检查文件权限
SENSITIVE_FILES=("/opt/qq-bot/.env" "/opt/qq-bot/app/config.yaml")

for file in "${SENSITIVE_FILES[@]}"; do
    if [ -f "$file" ]; then
        PERMISSIONS=$(stat -c "%a" "$file")
        if [ "$PERMISSIONS" -le 600 ]; then
            log_success "文件权限安全: $file ($PERMISSIONS)"
        else
            log_warn "文件权限过宽: $file ($PERMISSIONS)"
        fi
    fi
done

# 检查防火墙
if sudo ufw status | grep -q "Status: active"; then
    log_success "防火墙已启用"
else
    log_warn "防火墙未启用"
fi

echo ""

# 10. 生成验证报告
log_info "10. 生成验证报告..."

VALIDATION_REPORT="/opt/qq-bot/validation_report_$(date +%Y%m%d_%H%M%S).txt"

{
    echo "=== QQ交易机器人部署验证报告 ==="
    echo "生成时间: $(date)"
    echo "主机名: $(hostname)"
    echo ""
    echo "验证结果汇总:"
    echo "- 系统环境: $(if [ -n "$PYTHON_VERSION" ]; then echo '通过'; else echo '失败'; fi)"
    echo "- 应用程序: $(if [ -f "$APP_DIR/main.py" ]; then echo '通过'; else echo '失败'; fi)"
    echo "- 服务状态: $(if systemctl is-active --quiet "$SERVICE_NAME"; then echo '通过'; else echo '失败'; fi)"
    echo "- 网络连接: $(if ping -c 1 -W 3 api.binance.com >/dev/null 2>&1; then echo '通过'; else echo '失败'; fi)"
    echo "- 功能测试: $(if python3 -c 'import numpy' 2>/dev/null; then echo '通过'; else echo '失败'; fi)"
    echo ""
    echo "性能指标:"
    echo "- 内存使用率: ${MEMORY_USAGE}%"
    echo "- CPU使用率: ${CPU_USAGE}%"
    echo "- 磁盘I/O: ${DISK_IO} tps"
    echo ""
    echo "建议:"
    if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
        echo "- 考虑优化内存使用"
    fi
    if (( $(echo "$CPU_USAGE > 70" | bc -l) )); then
        echo "- 考虑优化CPU使用"
    fi
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "- 需要启动应用程序服务"
    fi
} > "$VALIDATION_REPORT"

log_success "验证报告已生成: $VALIDATION_REPORT"

echo ""
echo "=== 部署验证完成 ==="

# 返回总体状态
if systemctl is-active --quiet "$SERVICE_NAME" && [ -f "$APP_DIR/main.py" ] && [ -n "$PYTHON_VERSION" ]; then
    echo "总体状态: ✅ 部署成功"
    exit 0
else
    echo "总体状态: ❌ 部署存在问题"
    exit 1
fi
EOF

sudo chmod +x /opt/qq-bot/scripts/validate_deployment.sh
```

### 1.2 自动化验证流程

```bash
# 创建自动化验证脚本
sudo -u qqbot tee /opt/qq-bot/scripts/auto_validation.sh > /dev/null << 'EOF'
#!/bin/bash

# 自动化部署验证脚本

set -e

VALIDATION_RESULTS="/opt/qq-bot/validation_results.log"

# 运行验证脚本
/opt/qq-bot/scripts/validate_deployment.sh > "$VALIDATION_RESULTS" 2>&1

# 检查验证结果
if [ $? -eq 0 ]; then
    echo "✅ 部署验证通过" | tee -a "$VALIDATION_RESULTS"
    
    # 发送成功通知
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
             --data "{\"text\":\"🚀 QQ交易机器人部署验证成功 - $(hostname) - $(date)\"}" \
             "$SLACK_WEBHOOK"
    fi
else
    echo "❌ 部署验证失败" | tee -a "$VALIDATION_RESULTS"
    
    # 发送失败通知
    if [ -n "$SLACK_WEBHOOK" ]; then
        FAILED_ITEMS=$(grep -E "✗|失败" "$VALIDATION_RESULTS" | head -5)
        curl -X POST -H 'Content-type: application/json' \
             --data "{\"text\":\"❌ QQ交易机器人部署验证失败 - $(hostname)\\n失败项: $FAILED_ITEMS\"}" \
             "$SLACK_WEBHOOK"
    fi
    
    exit 1
fi
EOF

sudo chmod +x /opt/qq-bot/scripts/auto_validation.sh
```

## 2. 性能测试方案

### 2.1 基准性能测试

```bash
sudo -u qqbot tee /opt/qq-bot/scripts/performance_test.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人性能测试脚本

set -e

TEST_RESULTS="/opt/qq-bot/performance_test_$(date +%Y%m%d_%H%M%S).log"

# 性能测试函数
run_performance_test() {
    local test_name="$1"
    local command="$2"
    
    echo "=== 性能测试: $test_name ===" | tee -a "$TEST_RESULTS"
    echo "开始时间: $(date)" | tee -a "$TEST_RESULTS"
    
    # 记录开始时间
    local start_time=$(date +%s.%N)
    
    # 执行测试命令
    eval "$command" >> "$TEST_RESULTS" 2>&1
    
    # 记录结束时间
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    
    echo "测试耗时: ${duration}秒" | tee -a "$TEST_RESULTS"
    echo "" | tee -a "$TEST_RESULTS"
}

# 1. 系统性能基准测试
run_performance_test "系统基准测试" "
    echo 'CPU性能测试:'
    dd if=/dev/zero bs=1M count=1024 | md5sum
    
    echo '内存性能测试:'
    sysbench memory --memory-total-size=1G run
    
    echo '磁盘I/O测试:'
    sysbench fileio --file-total-size=1G --file-test-mode=rndrw prepare
    sysbench fileio --file-total-size=1G --file-test-mode=rndrw run
    sysbench fileio --file-total-size=1G --file-test-mode=rndrw cleanup
"

# 2. Python性能测试
run_performance_test "Python性能测试" "
    echo 'Python导入性能:'
    time python3 -c 'import numpy, pandas, websocket, binance, ccxt'
    
    echo '数据处理性能:'
    python3 << 'PYTHON_EOF'
import time
import numpy as np
import pandas as pd

# 大数据处理测试
start = time.time()
data = pd.DataFrame(np.random.randn(100000, 10))
result = data.describe()
end = time.time()
print(f'数据处理耗时: {end - start:.2f}秒')
PYTHON_EOF
"

# 3. 网络性能测试
run_performance_test "网络性能测试" "
    echo '网络延迟测试:'
    ping -c 10 api.binance.com | grep 'min/avg/max'
    
    echo '网络带宽测试:'
    speedtest-cli --simple
    
    echo 'WebSocket连接测试:'
    python3 << 'PYTHON_EOF'
import time
import websocket

def on_message(ws, message):
    print(f'收到消息: {len(message)} 字节')

def on_error(ws, error):
    print(f'错误: {error}')

def on_close(ws, close_status_code, close_msg):
    print('连接关闭')

def on_open(ws):
    print('连接已建立')
    ws.send('{\"method\": \"SUBSCRIBE\", \"params\": [\"btcusdt@ticker\"], \"id\": 1}')
    time.sleep(5)
    ws.close()

try:
    start = time.time()
    ws = websocket.WebSocketApp('wss://stream.binance.com:9443/ws',
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
    end = time.time()
    print(f'WebSocket测试耗时: {end - start:.2f}秒')
except Exception as e:
    print(f'WebSocket测试失败: {e}')
PYTHON_EOF
"

# 4. 应用程序性能测试
run_performance_test "应用程序性能测试" "
    echo '应用程序启动测试:'
    time sudo systemctl start qq-bot
    sleep 10
    
    echo '应用程序运行状态:'
    sudo systemctl status qq-bot
    
    echo '资源使用情况:'
    ps aux | grep qq-bot | grep -v grep
    
    # 停止应用程序
    sudo systemctl stop qq-bot
"

# 5. 生成性能报告
echo "=== 性能测试报告 ===" | tee -a "$TEST_RESULTS"
echo "生成时间: $(date)" | tee -a "$TEST_RESULTS"
echo "测试环境: $(hostname)" | tee -a "$TEST_RESULTS"
echo "" | tee -a "$TEST_RESULTS"

# 分析测试结果
echo "性能指标分析:" | tee -a "$TEST_RESULTS"

# 提取关键指标
CPU_SCORE=$(grep -A5 "CPU性能测试" "$TEST_RESULTS" | grep -oE '[0-9.]+ MB/s' | head -1 | sed 's/ MB\/s//')
MEMORY_SCORE=$(grep -A5 "内存性能测试" "$TEST_RESULTS" | grep -oE '[0-9.]+ MiB/sec' | head -1 | sed 's/ MiB\/sec//')
DISK_SCORE=$(grep -A5 "磁盘I/O测试" "$TEST_RESULTS" | grep -oE 'reads/s: [0-9.]+' | head -1 | sed 's/reads\/s: //')

{
    echo "CPU性能得分: ${CPU_SCORE:-N/A} MB/s"
    echo "内存性能得分: ${MEMORY_SCORE:-N/A} MiB/sec"
    echo "磁盘I/O得分: ${DISK_SCORE:-N/A} reads/s"
    echo ""
    
    # 性能评估
    if [ -n "$CPU_SCORE" ] && [ "$(echo "$CPU_SCORE > 500" | bc)" -eq 1 ]; then
        echo "CPU性能: ✅ 优秀"
    elif [ -n "$CPU_SCORE" ] && [ "$(echo "$CPU_SCORE > 200" | bc)" -eq 1 ]; then
        echo "CPU性能: ⚠ 良好"
    else
        echo "CPU性能: ❌ 需要优化"
    fi
    
    if [ -n "$MEMORY_SCORE" ] && [ "$(echo "$MEMORY_SCORE > 5000" | bc)" -eq 1 ]; then
        echo "内存性能: ✅ 优秀"
    elif [ -n "$MEMORY_SCORE" ] && [ "$(echo "$MEMORY_SCORE > 2000" | bc)" -eq 1 ]; then
        echo "内存性能: ⚠ 良好"
    else
        echo "内存性能: ❌ 需要优化"
    fi
} | tee -a "$TEST_RESULTS"

echo ""
echo "性能测试完成，详细结果见: $TEST_RESULTS"
EOF

sudo chmod +x /opt/qq-bot/scripts/performance_test.sh
```

### 2.2 负载测试脚本

```bash
sudo -u qqbot tee /opt/qq-bot/scripts/load_test.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人负载测试脚本

set -e

LOAD_TEST_RESULTS="/opt/qq-bot/load_test_$(date +%Y%m%d_%H%M%S).log"
DURATION=300  # 测试持续时间（秒）
CONCURRENT_USERS=10  # 并发用户数

echo "=== QQ交易机器人负载测试 ===" | tee "$LOAD_TEST_RESULTS"
echo "开始时间: $(date)" | tee -a "$LOAD_TEST_RESULTS"
echo "测试时长: $DURATION 秒" | tee -a "$LOAD_TEST_RESULTS"
echo "并发用户: $CONCURRENT_USERS" | tee -a "$LOAD_TEST_RESULTS"
echo "" | tee -a "$LOAD_TEST_RESULTS"

# 记录初始系统状态
echo "初始系统状态:" | tee -a "$LOAD_TEST_RESULTS"
top -bn1 | head -5 | tee -a "$LOAD_TEST_RESULTS"
free -h | tee -a "$LOAD_TEST_RESULTS"
echo "" | tee -a "$LOAD_TEST_RESULTS"

# 启动应用程序
sudo systemctl start qq-bot
sleep 10

# 负载测试函数
run_load_test() {
    local test_id="$1"
    local users="$2"
    local duration="$3"
    
    echo "开始负载测试 $test_id (用户数: $users, 时长: ${duration}秒)..." | tee -a "$LOAD_TEST_RESULTS"
    
    # 模拟并发请求（这里需要根据实际API设计）
    for i in $(seq 1 "$users"); do
        (
            # 模拟API调用
            python3 << 'PYTHON_EOF' &
import time
import requests
import random

start_time = time.time()
request_count = 0

while time.time() - start_time < $duration:
    try:
        # 模拟不同的API调用
        apis = [
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=10"
        ]
        
        response = requests.get(random.choice(apis), timeout=5)
        request_count += 1
        
        # 随机延迟
        time.sleep(random.uniform(0.1, 1.0))
    except Exception as e:
        print(f"请求失败: {e}")
        break

print(f"用户 {$i} 完成 {request_count} 次请求")
PYTHON_EOF
        ) &
    done
    
    # 等待所有请求完成
    wait
    
    echo "负载测试 $test_id 完成" | tee -a "$LOAD_TEST_RESULTS"
}

# 执行负载测试
run_load_test "基础负载" "$CONCURRENT_USERS" "$DURATION"

# 记录测试期间的系统状态
echo "" | tee -a "$LOAD_TEST_RESULTS"
echo "测试期间峰值状态:" | tee -a "$LOAD_TEST_RESULTS"

# 监控应用程序性能
APPLICATION_METRICS=(
    "CPU使用率: $(ps aux | grep qq-bot | grep -v grep | awk '{print $3}' | head -1)%"
    "内存使用: $(ps aux | grep qq-bot | grep -v grep | awk '{print $4}' | head -1)%"
    "虚拟内存: $(ps aux | grep qq-bot | grep -v grep | awk '{print $5}' | head -1) KB"
)

for metric in "${APPLICATION_METRICS[@]}"; do
    echo "$metric" | tee -a "$LOAD_TEST_RESULTS"
done

# 停止应用程序
sudo systemctl stop qq-bot

# 生成负载测试报告
echo "" | tee -a "$LOAD_TEST_RESULTS"
echo "=== 负载测试报告 ===" | tee -a "$LOAD_TEST_RESULTS"

# 分析性能指标
{
    echo "负载测试总结:"
    echo "- 测试时长: $DURATION 秒"
    echo "- 并发用户: $CONCURRENT_USERS"
    echo "- 应用程序稳定性: $(if systemctl is-active --quiet qq-bot; then echo '良好'; else echo '需要优化'; fi)"
    echo ""
    
    # 性能建议
    echo "性能优化建议:"
    if [ "$(ps aux | grep qq-bot | grep -v grep | awk '{print $3}' | head -1 | cut -d. -f1)" -gt 50 ]; then
        echo "- 考虑优化CPU密集型操作"
    fi
    
    if [ "$(ps aux | grep qq-bot | grep -v grep | awk '{print $4}' | head -1 | cut -d. -f1)" -gt 30 ]; then
        echo "- 考虑优化内存使用"
    fi
    
    echo "- 建议在生产环境进行更长时间的稳定性测试"
} | tee -a "$LOAD_TEST_RESULTS"

echo ""
echo "负载测试完成，详细结果见: $LOAD_TEST_RESULTS"
EOF

sudo chmod +x /opt/qq-bot/scripts/load_test.sh
```

## 3. 持续监控和优化

### 3.1 性能监控配置

```bash
# 创建性能监控脚本
sudo -u qqbot tee /opt/qq-bot/scripts/continuous_monitoring.sh > /dev/null << 'EOF'
#!/bin/bash

# 持续性能监控脚本

MONITOR_LOG="/opt/qq-bot/performance_monitor.log"
ALERT_THRESHOLD=80  # 告警阈值百分比

# 监控系统资源
monitor_system_resources() {
    local timestamp=$(date +%Y-%m-%dT%H:%M:%S)
    
    # CPU使用率
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    
    # 内存使用率
    local memory_usage=$(free | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')
    
    # 磁盘使用率
    local disk_usage=$(df /opt/qq-bot | tail -1 | awk '{print $5}' | sed 's/%//')
    
    # 应用程序状态
    local app_status=$(systemctl is-active qq-bot)
    
    # 记录监控数据
    echo "$timestamp | CPU: ${cpu_usage}% | 内存: ${memory_usage}% | 磁盘: ${disk_usage}% | 应用: $app_status" >> "$MONITOR_LOG"
    
    # 检查告警条件
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD" | bc -l) )); then
        echo "$(date): CPU使用率过高: ${cpu_usage}%" >> "/opt/qq-bot/alerts.log"
    fi
    
    if (( $(echo "$memory_usage > $ALERT_THRESHOLD" | bc -l) )); then
        echo "$(date): 内存使用率过高: ${memory_usage}%" >> "/opt/qq-bot/alerts.log"
    fi
    
    if (( $(echo "$disk_usage > $ALERT_THRESHOLD" | bc -l) )); then
        echo "$(date): 磁盘使用率过高: ${disk_usage}%" >> "/opt/qq-bot/alerts.log"
    fi
    
    if [ "$app_status" != "active" ]; then
        echo "$(date): 应用程序服务异常: $app_status" >> "/opt/qq-bot/alerts.log"
    fi
}

# 执行监控
monitor_system_resources

# 清理旧日志（保留最近7天）
find "/opt/qq-bot" -name "performance_monitor.log" -mtime +7 -exec tail -n 1000 {} > {}.tmp \; -exec mv {}.tmp {} \;
find "/opt/qq-bot" -name "alerts.log" -mtime +30 -delete
EOF

sudo chmod +x /opt/qq-bot/scripts/continuous_monitoring.sh

# 添加到crontab（每5分钟执行一次）
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/qq-bot/scripts/continuous_monitoring.sh > /dev/null 2>&1") | crontab -
```

这个完整的验证和性能测试方案确保了QQ交易机器人在云服务器上的稳定运行和良好性能。