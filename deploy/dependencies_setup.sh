#!/bin/bash

# QQ交易机器人依赖软件安装脚本

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

# 配置变量
APP_USER="qqbot"
APP_DIR="/opt/qq-bot"
VENV_PATH="$APP_DIR/.venv"

log_info "开始安装QQ交易机器人依赖软件..."

# 1. 检查系统环境
log_info "检查系统环境..."

# 检查Python版本
PYTHON_VERSION=$(python3.11 --version 2>/dev/null | cut -d' ' -f2)
if [ -z "$PYTHON_VERSION" ]; then
    log_error "Python 3.11未安装，请先运行server_setup.sh"
    exit 1
fi
log_info "Python版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    log_error "虚拟环境不存在，请先运行server_setup.sh"
    exit 1
fi

# 2. 安装系统级依赖
log_info "安装系统级依赖包..."

# 更新系统包
sudo apt update

# 安装编译依赖
sudo apt install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libpq-dev \
    curl \
    wget \
    git

# 3. 配置Python虚拟环境
log_info "配置Python虚拟环境..."

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 升级pip
pip install --upgrade pip

# 4. 安装Python依赖包
log_info "安装Python依赖包..."

# 创建requirements.txt文件
sudo -u $APP_USER tee "$APP_DIR/requirements.txt" > /dev/null << 'EOF'
# QQ交易机器人依赖包列表

# 核心依赖
PyYAML>=6.0
numpy>=1.26
pandas>=2.2
tabulate>=0.9
websocket-client>=1.8
python-binance>=1.0.19
ccxt>=4.4

# 数据分析
scipy>=1.11
scikit-learn>=1.3

# 网络和异步
requests>=2.31
aiohttp>=3.8
asyncio

# 工具类
python-dateutil>=2.8
pytz>=2023.3

# 监控和日志
psutil>=5.9

# 测试框架（可选）
pytest>=7.4
pytest-asyncio>=0.21

# 开发工具（可选）
black>=23.7
flake8>=6.0
mypy>=1.5
EOF

# 安装依赖包
log_info "安装Python包..."
pip install -r "$APP_DIR/requirements.txt"

# 5. 安装性能优化包（可选）
log_info "安装性能优化包..."

# 安装优化版本的numpy（如果支持）
pip install --upgrade numpy

# 安装内存优化工具
pip install memory_profiler

# 6. 配置应用程序环境
log_info "配置应用程序环境..."

# 创建应用程序目录结构
sudo -u $APP_USER mkdir -p "$APP_DIR/app" "$APP_DIR/data" "$APP_DIR/scripts"

# 创建生产环境配置文件模板
sudo -u $APP_USER tee "$APP_DIR/app/config.production.yaml" > /dev/null << 'EOF'
# QQ交易机器人生产环境配置

mode: "live"
data_mode: "websocket"

timeframe: "5m"

runtime:
  loop_interval_seconds: 0.5
  heartbeat_interval_seconds: 60
  max_loops: 0

experiment:
  active_strategy_profile: "aggressive"
  baseline_strategy_profile: "baseline"
  compare_profiles: ["baseline", "aggressive"]

data:
  warmup_candles: 200
  websocket_reconnect_seconds: 5
  websocket_stale_seconds: 75

portfolio:
  max_open_positions: 3

radar:
  enabled: true
  max_hot_symbols: 10
  min_24h_volume: 10000000
  update_interval: 60
  price_weight: 0.6
  funding_weight: 0.4
  min_score: 24.0
  quote_asset: "USDT"
  exclude_symbols: []
  always_include_symbols: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
  fallback_symbols: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

risk:
  starting_balance_usdt: 1000
  risk_per_trade: 0.01
  max_daily_loss_pct: 0.03
  max_consecutive_losses: 2
  cooldown_minutes: 15
  leverage: 1
  min_notional_usdt: 25
  max_notional_usdt: 100

strategy:
  lookback: 50
  ema_period: 21
  vwap_window: 20

logging:
  level: "INFO"
  file: "/var/log/qq-bot/bot.log"
  error_file: "/var/log/qq-bot/error.log"
  detailed_file: "/var/log/qq-bot/detailed.log"
  max_file_size: 104857600  # 100MB
  backup_count: 10
EOF

# 7. 安装监控工具
log_info "安装系统监控工具..."

# 安装基础监控工具
sudo apt install -y htop iotop nload nethogs

# 安装进程监控工具
sudo apt install -y supervisor

# 配置supervisor（如果需要）
sudo tee /etc/supervisor/conf.d/qq-bot.conf > /dev/null << EOF
[program:qq-bot]
command=/opt/qq-bot/start.sh
directory=/opt/qq-bot/app
user=qqbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/qq-bot/supervisor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
EOF

# 8. 安装日志管理工具
log_info "安装日志管理工具..."

# 安装日志轮转工具（已包含在基础包中）
# 配置额外的日志收集工具（可选）

# 9. 安装网络工具
log_info "安装网络诊断工具..."

sudo apt install -y \
    net-tools \
    dnsutils \
    traceroute \
    tcpdump \
    nmap

# 10. 安装备份工具
log_info "安装数据备份工具..."

sudo apt install -y \
    rsync \
    rclone \
    duplicity

# 11. 配置性能优化
log_info "配置系统性能优化..."

# 创建性能优化脚本
sudo -u $APP_USER tee "$APP_DIR/scripts/optimize_performance.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人性能优化脚本

set -e

echo "=== 性能优化配置 ==="

# 1. 优化Python垃圾回收
export PYTHONGCENABLE=1
export PYTHONGCTHRESHOLD=10000

# 2. 优化Pandas性能
export PANDAS_MEMORY_MAP=true

# 3. 设置NumPy线程数
export OMP_NUM_THREADS=2

# 4. 优化网络连接
echo "net.core.rmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_rmem = 4096 87380 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_wmem = 4096 16384 16777216" | sudo tee -a /etc/sysctl.conf

sudo sysctl -p

echo "性能优化配置完成"
EOF

sudo chmod +x "$APP_DIR/scripts/optimize_performance.sh"

# 12. 验证安装结果
log_info "验证依赖安装结果..."

# 检查Python包安装
echo "=== 已安装的Python包 ==="
pip list | grep -E "(numpy|pandas|websocket|binance|ccxt)"

# 检查系统工具
echo "=== 系统工具检查 ==="
for tool in python3.11 pip htop nload; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✓ $tool 已安装"
    else
        echo "✗ $tool 未安装"
    fi
done

# 13. 创建环境检查脚本
log_info "创建环境检查脚本..."

sudo -u $APP_USER tee "$APP_DIR/scripts/check_environment.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人环境检查脚本

echo "=== 环境检查报告 ==="
echo "检查时间: $(date)"
echo ""

# 1. 系统信息
echo "1. 系统信息:"
echo "   主机名: $(hostname)"
echo "   系统版本: $(lsb_release -d | cut -f2) ($(uname -r))"
echo "   CPU核心: $(nproc)"
echo "   内存总量: $(free -h | awk '/^Mem:/{print $2}')"
echo ""

# 2. Python环境
echo "2. Python环境:"
echo "   Python版本: $(python3.11 --version 2>/dev/null || echo '未安装')"
echo "   PIP版本: $(pip --version 2>/dev/null | cut -d' ' -f2 || echo '未安装')"
echo "   虚拟环境: $(which python | grep -q ".venv" && echo "已激活" || echo "未激活")"
echo ""

# 3. 关键依赖包
echo "3. 关键依赖包:"
for pkg in numpy pandas websocket-client python-binance ccxt; do
    version=$(pip show "$pkg" 2>/dev/null | grep "Version" | cut -d' ' -f2)
    if [ -n "$version" ]; then
        echo "   ✓ $pkg: $version"
    else
        echo "   ✗ $pkg: 未安装"
    fi
done
echo ""

# 4. 网络连接检查
echo "4. 网络连接检查:"
for host in api.binance.com stream.binance.com; do
    if ping -c 1 -W 3 "$host" >/dev/null 2>&1; then
        echo "   ✓ 可以连接到 $host"
    else
        echo "   ✗ 无法连接到 $host"
    fi
done
echo ""

# 5. 磁盘空间检查
echo "5. 磁盘空间:"
df -h /opt/qq-bot | tail -1 | awk '{print "   可用空间: " $4 "/" $2 " (" $5 " 使用率)"}'
echo ""

# 6. 服务状态检查
echo "6. 服务状态:"
if systemctl is-active --quiet qq-bot; then
    echo "   ✓ qq-bot服务: 运行中"
else
    echo "   ✗ qq-bot服务: 未运行"
fi

if systemctl is-active --quiet supervisor; then
    echo "   ✓ supervisor服务: 运行中"
else
    echo "   ✗ supervisor服务: 未运行"
fi
echo ""

echo "=== 检查完成 ==="
EOF

sudo chmod +x "$APP_DIR/scripts/check_environment.sh"

# 14. 创建依赖更新脚本
log_info "创建依赖更新脚本..."

sudo -u $APP_USER tee "$APP_DIR/scripts/update_dependencies.sh" > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人依赖更新脚本

set -e

APP_DIR="/opt/qq-bot"
VENV_PATH="$APP_DIR/.venv"

# 激活虚拟环境
source "$VENV_PATH/bin/activate"

# 备份当前依赖状态
pip freeze > "$APP_DIR/backups/requirements_$(date +%Y%m%d_%H%M%S).txt"

# 更新pip
pip install --upgrade pip

# 更新所有包
pip install --upgrade -r "$APP_DIR/requirements.txt"

# 检查安全更新
pip list --outdated --format=columns

echo "依赖更新完成"
EOF

sudo chmod +x "$APP_DIR/scripts/update_dependencies.sh"

log_info "依赖软件安装完成！"

# 显示安装总结
cat << EOF

=== 安装完成总结 ===

✅ 系统级依赖已安装
✅ Python虚拟环境已配置
✅ 交易相关包已安装
✅ 监控工具已配置
✅ 性能优化脚本已创建

重要文件位置：
- 虚拟环境: $VENV_PATH/
- 依赖列表: $APP_DIR/requirements.txt
- 配置模板: $APP_DIR/app/config.production.yaml
- 环境检查: $APP_DIR/scripts/check_environment.sh
- 性能优化: $APP_DIR/scripts/optimize_performance.sh

下一步操作：
1. 上传应用程序代码到 $APP_DIR/app/
2. 配置生产环境参数
3. 运行环境检查脚本: $APP_DIR/scripts/check_environment.sh
4. 启动应用程序服务

环境检查命令：
sudo -u qqbot $APP_DIR/scripts/check_environment.sh
EOF