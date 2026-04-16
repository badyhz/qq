# QQ交易机器人性能优化指南

## 1. 系统级性能优化

### 1.1 内核参数优化

```bash
# 创建系统优化脚本
sudo tee /opt/qq-bot/scripts/optimize_system.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人系统性能优化脚本

set -e

# 备份原始配置
sudo cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d)

# 应用性能优化参数
sudo tee -a /etc/sysctl.conf > /dev/null << 'SYSCTL_EOF'

# QQ交易机器人性能优化配置

# 网络优化
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_tw_recycle = 0
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.vfs_cache_pressure = 50

# 文件系统优化
fs.file-max = 1000000
fs.nr_open = 1000000

# 网络缓冲区优化
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 16384 16777216
net.ipv4.udp_rmem_min = 16384
net.ipv4.udp_wmem_min = 16384

SYSCTL_EOF

# 应用配置
sudo sysctl -p

# 配置I/O调度器（针对SSD优化）
if [ -f /sys/block/sda/queue/scheduler ]; then
    echo 'deadline' | sudo tee /sys/block/sda/queue/scheduler
    echo "I/O调度器已设置为: deadline"
fi

# 配置CPU性能模式
if command -v cpupower >/dev/null 2>&1; then
    sudo cpupower frequency-set -g performance
    echo "CPU性能模式已启用"
fi

echo "系统性能优化完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/optimize_system.sh
```

### 1.2 服务资源限制配置

```bash
# 优化systemd服务资源限制
sudo tee /etc/systemd/system/qq-bot.service.d/limits.conf > /dev/null << 'EOF'
[Service]
# 内存限制
MemoryMax=2G
MemoryHigh=1.5G

# CPU限制
CPUQuota=80%
CPUWeight=100

# I/O限制
IOWeight=100

# 进程限制
TasksMax=1000

# 安全限制
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/qq-bot /var/log/qq-bot
EOF

sudo systemctl daemon-reload
```

## 2. 应用程序性能优化

### 2.1 Python运行时优化

```bash
# 创建Python优化配置
sudo -u qqbot tee /opt/qq-bot/scripts/optimize_python.sh > /dev/null << 'EOF'
#!/bin/bash

# Python运行时性能优化

set -e

# 设置环境变量
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export PYTHONHASHSEED=random

# GIL优化（对于I/O密集型应用）
export PYTHON_GIL=0

# 内存管理优化
export PYTHONMALLOC=malloc
export MALLOC_TRIM_THRESHOLD_=65536

# NumPy性能优化
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2

# Pandas性能优化
export PANDAS_MEMORY_MAP=true

# 网络优化
export WEBSOCKET_CLIENT_TIMEOUT=30
export WEBSOCKET_CLIENT_BUFFER_SIZE=65536

echo "Python运行时优化配置完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/optimize_python.sh
```

### 2.2 应用程序代码优化

```python
# 在应用程序启动脚本中添加性能优化
sudo -u qqbot tee -a /opt/qq-bot/start.sh > /dev/null << 'PYTHON_EOF'

# 性能优化配置
import os
os.environ['OMP_NUM_THREADS'] = '2'
os.environ['MKL_NUM_THREADS'] = '2'

# 禁用调试模式
import sys
if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
    # 调试模式下禁用优化
    pass
else:
    # 生产环境优化
    import numpy as np
    np.seterr(all='ignore')  # 忽略数值警告
    
    import pandas as pd
    pd.set_option('mode.chained_assignment', None)  # 禁用链式赋值警告

PYTHON_EOF
```

## 3. 数据库和存储优化

### 3.1 文件I/O优化

```bash
# 创建存储优化脚本
sudo -u qqbot tee /opt/qq-bot/scripts/optimize_storage.sh > /dev/null << 'EOF'
#!/bin/bash

# 存储性能优化脚本

set -e

# 检查当前文件系统
CURRENT_FS=$(df /opt/qq-bot | tail -1 | awk '{print $1}')
FS_TYPE=$(lsblk -f "$CURRENT_FS" | tail -1 | awk '{print $2}')

echo "当前文件系统: $CURRENT_FS ($FS_TYPE)"

# 针对不同文件系统的优化建议
case "$FS_TYPE" in
    "ext4")
        echo "检测到ext4文件系统，建议优化:"
        echo "- 启用noatime挂载选项"
        echo "- 调整日志模式为ordered"
        echo "- 启用dir_index特性"
        ;;
    "xfs")
        echo "检测到xfs文件系统，建议优化:"
        echo "- 调整inode大小"
        echo "- 优化分配组大小"
        ;;
    *)
        echo "未知文件系统类型: $FS_TYPE"
        ;;
esac

# 创建优化的挂载选项（如果控制挂载点）
if mount | grep -q "/opt/qq-bot"; then
    echo "当前挂载选项: $(mount | grep "/opt/qq-bot" | awk '{print $6}')"
    echo ""
    echo "建议挂载选项: defaults,noatime,nodiratime,data=writeback,barrier=0"
fi

# 优化文件描述符限制
echo ""
echo "当前文件描述符限制:"
ulimit -n

echo "建议设置: ulimit -n 100000"

# 创建临时文件清理脚本
sudo -u qqbot tee /opt/qq-bot/scripts/cleanup_temp.sh > /dev/null << 'CLEANUP_EOF'
#!/bin/bash

# 临时文件清理脚本

find /opt/qq-bot/tmp -type f -mtime +1 -delete
find /opt/qq-bot/logs -name "*.log.*" -mtime +7 -delete
find /tmp -name "qq-bot-*" -mtime +1 -delete

# 清理Python缓存
find /opt/qq-bot -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find /opt/qq-bot -name "*.pyc" -delete

CLEANUP_EOF

sudo chmod +x /opt/qq-bot/scripts/cleanup_temp.sh

echo "存储优化建议生成完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/optimize_storage.sh
```

## 4. 网络性能优化

### 4.1 网络栈优化

```bash
# 创建网络优化脚本
sudo tee /opt/qq-bot/scripts/optimize_network.sh > /dev/null << 'EOF'
#!/bin/bash

# 网络性能优化脚本

set -e

# 检查当前网络配置
echo "当前网络配置:"
cat /proc/sys/net/ipv4/tcp_fin_timeout
cat /proc/sys/net/ipv4/tcp_keepalive_time
cat /proc/sys/net/core/somaxconn

echo ""

# 应用网络优化（如果权限允许）
if [ "$EUID" -eq 0 ]; then
    echo "应用网络优化配置..."
    
    # TCP优化
    echo 30 > /proc/sys/net/ipv4/tcp_fin_timeout
    echo 300 > /proc/sys/net/ipv4/tcp_keepalive_time
    echo 65535 > /proc/sys/net/core/somaxconn
    
    # 缓冲区优化
    echo 16777216 > /proc/sys/net/core/rmem_max
    echo 16777216 > /proc/sys/net/core/wmem_max
    echo "4096 87380 16777216" > /proc/sys/net/ipv4/tcp_rmem
    echo "4096 16384 16777216" > /proc/sys/net/ipv4/tcp_wmem
    
    echo "网络优化配置已应用"
else
    echo "需要root权限应用网络优化"
    echo "请以sudo权限运行此脚本"
fi

# DNS优化建议
echo ""
echo "DNS优化建议:"
echo "1. 配置本地DNS缓存（如systemd-resolved）"
echo "2. 使用可靠的DNS服务器（如8.8.8.8, 1.1.1.1）"
echo "3. 配置DNS超时和重试策略"

# 网络连接测试
echo ""
echo "网络连接测试:"

# 测试交易所API连接延迟
for host in api.binance.com stream.binance.com; do
    echo -n "$host: "
    ping -c 1 -W 3 "$host" 2>/dev/null | grep -oP 'time=\K[0-9.]+' || echo "超时"
done

echo "网络优化建议生成完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/optimize_network.sh
```

## 5. 监控和调优工具

### 5.1 性能监控仪表板

```bash
# 创建实时性能监控脚本
sudo -u qqbot tee /opt/qq-bot/scripts/performance_dashboard.sh > /dev/null << 'EOF'
#!/bin/bash

# 实时性能监控仪表板

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 清屏并显示标题
clear
echo -e "${BLUE}=== QQ交易机器人性能监控仪表板 ===${NC}"
echo -e "更新时间: $(date)"
echo ""

while true; do
    # 获取系统性能指标
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    MEMORY_USAGE=$(free | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')
    LOAD_AVG=$(cat /proc/loadavg | awk '{print $1}')
    DISK_USAGE=$(df /opt/qq-bot | tail -1 | awk '{print $5}')
    
    # 获取应用程序指标
    if systemctl is-active --quiet qq-bot; then
        APP_STATUS="${GREEN}运行中${NC}"
        APP_CPU=$(ps aux | grep "python main.py" | grep -v grep | awk '{print $3}' | head -1)
        APP_MEM=$(ps aux | grep "python main.py" | grep -v grep | awk '{print $4}' | head -1)
    else
        APP_STATUS="${RED}未运行${NC}"
        APP_CPU="N/A"
        APP_MEM="N/A"
    fi
    
    # 获取网络指标
    NETWORK_RX=$(cat /proc/net/dev | grep eth0 | awk '{print $2}')
    NETWORK_TX=$(cat /proc/net/dev | grep eth0 | awk '{print $10}')
    
    # 清屏并显示最新数据
    clear
    echo -e "${BLUE}=== QQ交易机器人性能监控仪表板 ===${NC}"
    echo -e "更新时间: $(date)"
    echo ""
    
    # 系统资源
    echo -e "${YELLOW}系统资源:${NC}"
    printf "CPU使用率: %s%% | 内存使用率: %s%% | 负载: %s | 磁盘使用率: %s\n" \
        "$CPU_USAGE" "$MEMORY_USAGE" "$LOAD_AVG" "$DISK_USAGE"
    echo ""
    
    # 应用程序状态
    echo -e "${YELLOW}应用程序状态:${NC}"
    printf "服务状态: %s | CPU: %s%% | 内存: %s%%\n" "$APP_STATUS" "${APP_CPU:-0}" "${APP_MEM:-0}"
    echo ""
    
    # 网络状态
    echo -e "${YELLOW}网络状态:${NC}"
    printf "接收: %s bytes | 发送: %s bytes\n" "$NETWORK_RX" "$NETWORK_TX"
    echo ""
    
    # 性能建议
    echo -e "${YELLOW}性能建议:${NC}"
    
    if (( $(echo "$CPU_USAGE > 80" | bc -l) )); then
        echo -e "${RED}⚠ CPU使用率过高，考虑优化计算密集型操作${NC}"
    elif (( $(echo "$CPU_USAGE > 60" | bc -l) )); then
        echo -e "${YELLOW}ℹ CPU使用率适中，监控变化${NC}"
    else
        echo -e "${GREEN}✓ CPU使用率正常${NC}"
    fi
    
    if (( $(echo "$MEMORY_USAGE > 80" | bc -l) )); then
        echo -e "${RED}⚠ 内存使用率过高，考虑优化内存使用${NC}"
    elif (( $(echo "$MEMORY_USAGE > 60" | bc -l) )); then
        echo -e "${YELLOW}ℹ 内存使用率适中，监控变化${NC}"
    else
        echo -e "${GREEN}✓ 内存使用率正常${NC}"
    fi
    
    echo ""
    echo "按 Ctrl+C 退出监控"
    
    # 等待2秒后刷新
    sleep 2

done
EOF

sudo chmod +x /opt/qq-bot/scripts/performance_dashboard.sh
```

### 5.2 自动化性能调优

```bash
# 创建自动化性能调优脚本
sudo -u qqbot tee /opt/qq-bot/scripts/auto_tuning.sh > /dev/null << 'EOF'
#!/bin/bash

# 自动化性能调优脚本

set -e

TUNING_LOG="/opt/qq-bot/auto_tuning.log"

# 记录调优操作
log_tuning() {
    echo "[$(date)] $1" >> "$TUNING_LOG"
}

# 检查当前性能状态
check_performance() {
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local memory_usage=$(free | awk '/Mem:/ {printf("%.1f", $3/$2 * 100)}')
    local load_avg=$(cat /proc/loadavg | awk '{print $1}')
    
    echo "$cpu_usage $memory_usage $load_avg"
}

# 根据性能状态进行调优
auto_tune() {
    local metrics=($(check_performance))
    local cpu_usage="${metrics[0]}"
    local memory_usage="${metrics[1]}"
    local load_avg="${metrics[2]}"
    
    log_tuning "当前性能: CPU=${cpu_usage}% MEM=${memory_usage}% LOAD=${load_avg}"
    
    # CPU使用率过高调优
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_tuning "CPU使用率过高，进行优化"
        
        # 降低应用程序CPU限制
        sudo systemctl set-property qq-bot CPUQuota=60%
        
        # 调整Python线程数
        export OMP_NUM_THREADS=1
        export MKL_NUM_THREADS=1
    elif (( $(echo "$cpu_usage < 30" | bc -l) )); then
        log_tuning "CPU使用率较低，恢复默认设置"
        sudo systemctl set-property qq-bot CPUQuota=80%
        export OMP_NUM_THREADS=2
        export MKL_NUM_THREADS=2
    fi
    
    # 内存使用率过高调优
    if (( $(echo "$memory_usage > 85" | bc -l) )); then
        log_tuning "内存使用率过高，进行优化"
        
        # 清理缓存
        sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
        
        # 重启应用程序（如果配置了自动重启）
        if systemctl is-active --quiet qq-bot; then
            sudo systemctl restart qq-bot
            log_tuning "应用程序已重启以释放内存"
        fi
    fi
    
    # 负载过高调优
    if (( $(echo "$load_avg > $(nproc)" | bc -l) )); then
        log_tuning "系统负载过高，进行优化"
        
        # 降低进程优先级
        sudo renice 10 $(pgrep -f "python main.py" 2>/dev/null) 2>/dev/null || true
    fi
}

# 执行自动调优
auto_tune

# 清理旧日志
find "/opt/qq-bot" -name "auto_tuning.log" -mtime +7 -exec tail -n 1000 {} > {}.tmp \; -exec mv {}.tmp {} \;

echo "自动性能调优完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/auto_tuning.sh

# 添加到crontab（每小时执行一次）
(crontab -l 2>/dev/null; echo "0 * * * * /opt/qq-bot/scripts/auto_tuning.sh > /dev/null 2>&1") | crontab -
```

## 6. 性能基准和报告

### 6.1 性能基准测试

```bash
# 创建性能基准测试脚本
sudo -u qqbot tee /opt/qq-bot/scripts/benchmark.sh > /dev/null << 'EOF'
#!/bin/bash

# 性能基准测试脚本

set -e

BENCHMARK_FILE="/opt/qq-bot/benchmark_$(date +%Y%m%d_%H%M%S).log"

echo "=== QQ交易机器人性能基准测试 ===" | tee "$BENCHMARK_FILE"
echo "测试时间: $(date)" | tee -a "$BENCHMARK_FILE"
echo "" | tee -a "$BENCHMARK_FILE"

# 系统基准测试
echo "1. 系统基准测试:" | tee -a "$BENCHMARK_FILE"

# CPU性能
echo "- CPU性能测试:" | tee -a "$BENCHMARK_FILE"
{ time dd if=/dev/zero bs=1M count=100 2>/dev/null | md5sum > /dev/null; } 2>&1 | grep real | tee -a "$BENCHMARK_FILE"

# 内存性能
echo "- 内存性能测试:" | tee -a "$BENCHMARK_FILE"
{ time sysbench memory --memory-total-size=1G run; } 2>&1 | grep -E "(total time|transferred)" | tee -a "$BENCHMARK_FILE"

# 磁盘I/O性能
echo "- 磁盘I/O测试:" | tee -a "$BENCHMARK_FILE"
{ time dd if=/dev/zero of=/tmp/testfile bs=1M count=100 conv=fdatasync; } 2>&1 | grep copied | tee -a "$BENCHMARK_FILE"
rm -f /tmp/testfile

echo "" | tee -a "$BENCHMARK_FILE"

# 应用程序基准测试
echo "2. 应用程序基准测试:" | tee -a "$BENCHMARK_FILE"

# 启动时间测试
sudo systemctl stop qq-bot 2>/dev/null || true
{ time sudo systemctl start qq-bot; } 2>&1 | grep real | tee -a "$BENCHMARK_FILE"
sleep 5

# API响应测试
{ time curl -s "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" > /dev/null; } 2>&1 | grep real | tee -a "$BENCHMARK_FILE"

echo "" | tee -a "$BENCHMARK_FILE"

# 生成基准报告
echo "=== 性能基准报告 ===" | tee -a "$BENCHMARK_FILE"
echo "" | tee -a "$BENCHMARK_FILE"

# 性能评级
CPU_SCORE=$(dd if=/dev/zero bs=1M count=100 2>/dev/null | md5sum 2>&1 | grep -oE '[0-9.]+' | head -1)
MEM_SCORE=$(sysbench memory --memory-total-size=1G run 2>/dev/null | grep -oE '[0-9.]+ MiB/sec' | head -1)

echo "性能评级:" | tee -a "$BENCHMARK_FILE"
if (( $(echo "$CPU_SCORE > 500" | bc -l) )); then
    echo "- CPU性能: 优秀" | tee -a "$BENCHMARK_FILE"
elif (( $(echo "$CPU_SCORE > 200" | bc -l) )); then
    echo "- CPU性能: 良好" | tee -a "$BENCHMARK_FILE"
else
    echo "- CPU性能: 需要优化" | tee -a "$BENCHMARK_FILE"
fi

echo "" | tee -a "$BENCHMARK_FILE"
echo "基准测试完成，详细结果见: $BENCHMARK_FILE"
EOF

sudo chmod +x /opt/qq-bot/scripts/benchmark.sh
```

这个完整的性能优化方案确保了QQ交易机器人在云服务器上获得最佳性能表现。