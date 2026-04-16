# QQ交易机器人数据存储配置

## 1. 存储架构概述

QQ交易机器人采用轻量级文件存储架构，主要特点：

- **交易数据**: CSV文件存储（trades.csv）
- **配置文件**: YAML格式（config.yaml）
- **日志文件**: 文本格式轮转存储
- **临时数据**: 内存缓存 + 文件持久化

## 2. 文件存储配置

### 目录结构设计

```
/opt/qq-bot/
├── app/                    # 应用程序代码
│   ├── config.yaml        # 主配置文件
│   └── ...
├── data/                   # 数据存储目录
│   ├── trades/            # 交易记录
│   │   ├── trades.csv     # 当前交易记录
│   │   └── archive/       # 历史交易归档
│   ├── cache/             # 缓存数据
│   └── backups/           # 自动备份
├── logs/                   # 日志文件
│   ├── bot.log           # 运行日志
│   ├── error.log         # 错误日志
│   └── detailed.log      # 详细日志
└── tmp/                   # 临时文件
```

### 权限配置

```bash
# 创建目录结构
sudo -u qqbot mkdir -p /opt/qq-bot/data/{trades/archive,cache,backups}
sudo -u qqbot mkdir -p /opt/qq-bot/logs /opt/qq-bot/tmp

# 设置权限
sudo chmod 755 /opt/qq-bot/data /opt/qq-bot/logs
sudo chmod 700 /opt/qq-bot/data/trades /opt/qq-bot/tmp
```

## 3. 数据备份策略

### 自动备份脚本

```bash
sudo -u qqbot tee /opt/qq-bot/scripts/backup_data.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人数据备份脚本

set -e

BACKUP_DIR="/opt/qq-bot/data/backups"
DATA_DIR="/opt/qq-bot/data"
LOG_DIR="/opt/qq-bot/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="qq-bot-data-backup-${TIMESTAMP}.tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 执行备份
echo "开始备份数据..."
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    "$DATA_DIR/trades/trades.csv" \
    "$DATA_DIR/trades/archive/" \
    "$LOG_DIR/" 2>/dev/null || true

# 验证备份文件
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    echo "备份成功: $BACKUP_FILE ($BACKUP_SIZE)"
    
    # 记录备份日志
    echo "$(date): 数据备份完成 - $BACKUP_FILE ($BACKUP_SIZE)" >> "$LOG_DIR/backup.log"
else
    echo "备份失败: 文件未创建"
    exit 1
fi

# 清理旧备份（保留最近30天）
find "$BACKUP_DIR" -name "qq-bot-data-backup-*.tar.gz" -mtime +30 -delete

echo "备份完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/backup_data.sh
```

### 定时备份配置

```bash
# 添加到crontab
sudo -u qqbot crontab -l | { cat; echo "0 2 * * * /opt/qq-bot/scripts/backup_data.sh > /dev/null 2>&1"; } | sudo -u qqbot crontab -

# 每周归档交易数据
sudo -u qqbot tee /opt/qq-bot/scripts/archive_trades.sh > /dev/null << 'EOF'
#!/bin/bash

# 交易数据归档脚本

set -e

TRADES_FILE="/opt/qq-bot/data/trades/trades.csv"
ARCHIVE_DIR="/opt/qq-bot/data/trades/archive"
TIMESTAMP=$(date +%Y%m%d)

if [ -f "$TRADES_FILE" ]; then
    # 创建周归档
    ARCHIVE_FILE="$ARCHIVE_DIR/trades_week_$(date +%Y-%U).csv"
    
    # 如果文件存在，追加内容
    if [ -f "$ARCHIVE_FILE" ]; then
        tail -n +2 "$TRADES_FILE" >> "$ARCHIVE_FILE"
    else
        cp "$TRADES_FILE" "$ARCHIVE_FILE"
    fi
    
    # 清空当前交易文件（保留表头）
    head -n 1 "$TRADES_FILE" > "$TRADES_FILE.tmp"
    mv "$TRADES_FILE.tmp" "$TRADES_FILE"
    
    echo "交易数据已归档: $ARCHIVE_FILE"
fi
EOF

sudo chmod +x /opt/qq-bot/scripts/archive_trades.sh

# 每周日凌晨执行归档
sudo -u qqbot crontab -l | { cat; echo "0 3 * * 0 /opt/qq-bot/scripts/archive_trades.sh > /dev/null 2>&1"; } | sudo -u qqbot crontab -
```

## 4. 数据完整性检查

### 健康检查脚本

```bash
sudo -u qqbot tee /opt/qq-bot/scripts/check_data_integrity.sh > /dev/null << 'EOF'
#!/bin/bash

# 数据完整性检查脚本

echo "=== 数据完整性检查 ==="
echo "检查时间: $(date)"
echo ""

# 1. 检查交易文件
TRADES_FILE="/opt/qq-bot/data/trades/trades.csv"
if [ -f "$TRADES_FILE" ]; then
    FILE_SIZE=$(du -h "$TRADES_FILE" | cut -f1)
    LINE_COUNT=$(wc -l < "$TRADES_FILE")
    echo "✓ 交易文件存在: $TRADES_FILE ($FILE_SIZE, $LINE_COUNT 行)"
    
    # 检查文件格式
    if [ "$LINE_COUNT" -gt 0 ]; then
        HEADER=$(head -n 1 "$TRADES_FILE")
        EXPECTED_HEADER="timestamp,symbol,side,quantity,price,pnl,status"
        if [[ "$HEADER" == "$EXPECTED_HEADER"* ]]; then
            echo "✓ 文件格式正确"
        else
            echo "✗ 文件格式异常: $HEADER"
        fi
    fi
else
    echo "✗ 交易文件不存在"
fi
echo ""

# 2. 检查日志文件
LOG_FILES=("/opt/qq-bot/logs/bot.log" "/opt/qq-bot/logs/error.log")
for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        LOG_SIZE=$(du -h "$log_file" | cut -f1)
        echo "✓ 日志文件存在: $log_file ($LOG_SIZE)"
    else
        echo "✗ 日志文件不存在: $log_file"
    fi
done
echo ""

# 3. 检查磁盘空间
echo "磁盘空间检查:"
df -h /opt/qq-bot | tail -1 | awk '{print "   可用空间: " $4 "/" $2 " (" $5 " 使用率)"}'
echo ""

# 4. 检查备份文件
BACKUP_COUNT=$(find /opt/qq-bot/data/backups -name "*.tar.gz" -type f | wc -l)
if [ "$BACKUP_COUNT" -gt 0 ]; then
    LATEST_BACKUP=$(find /opt/qq-bot/data/backups -name "*.tar.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")
    BACKUP_AGE=$(($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")))
    BACKUP_AGE_DAYS=$((BACKUP_AGE / 86400))
    
    echo "✓ 备份文件数量: $BACKUP_COUNT"
    echo "   最新备份: $(basename "$LATEST_BACKUP") ($BACKUP_AGE_DAYS 天前)"
    
    if [ "$BACKUP_AGE_DAYS" -gt 7 ]; then
        echo "⚠ 警告: 最新备份超过7天"
    fi
else
    echo "✗ 没有找到备份文件"
fi
echo ""

echo "=== 检查完成 ==="
EOF

sudo chmod +x /opt/qq-bot/scripts/check_data_integrity.sh
```

## 5. 性能优化配置

### 文件系统优化

```bash
# 检查当前文件系统设置
sudo tune2fs -l /dev/your-device | grep -E "(Default mount options|Filesystem features)"

# 优化挂载选项（如果使用ext4）
# 在 /etc/fstab 中添加以下选项：
# defaults,noatime,nodiratime,data=writeback,barrier=0
```

### I/O调度优化

```bash
# 查看当前I/O调度器
cat /sys/block/sda/queue/scheduler

# 设置为deadline或noop（对于SSD）
echo 'deadline' | sudo tee /sys/block/sda/queue/scheduler
```

## 6. 监控和告警

### 磁盘空间监控

```bash
# 创建磁盘监控脚本
sudo -u qqbot tee /opt/qq-bot/scripts/monitor_disk.sh > /dev/null << 'EOF'
#!/bin/bash

# 磁盘空间监控脚本

THRESHOLD=80  # 使用率阈值百分比
CURRENT_USAGE=$(df /opt/qq-bot | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$CURRENT_USAGE" -gt "$THRESHOLD" ]; then
    echo "警告: 磁盘使用率超过 ${THRESHOLD}% (当前: ${CURRENT_USAGE}%)"
    
    # 发送告警（可根据需要集成邮件、短信等）
    echo "$(date): 磁盘使用率 ${CURRENT_USAGE}%" >> /opt/qq-bot/logs/alert.log
    
    # 自动清理临时文件
    find /opt/qq-bot/tmp -type f -mtime +1 -delete
    find /opt/qq-bot/logs -name "*.log.*" -mtime +7 -delete
fi
EOF

sudo chmod +x /opt/qq-bot/scripts/monitor_disk.sh

# 每小时检查一次
sudo -u qqbot crontab -l | { cat; echo "0 * * * * /opt/qq-bot/scripts/monitor_disk.sh > /dev/null 2>&1"; } | sudo -u qqbot crontab -
```

## 7. 数据恢复流程

### 恢复脚本

```bash
sudo -u qqbot tee /opt/qq-bot/scripts/restore_data.sh > /dev/null << 'EOF'
#!/bin/bash

# 数据恢复脚本

set -e

BACKUP_DIR="/opt/qq-bot/data/backups"
RESTORE_DIR="/opt/qq-bot/data"

# 显示可用备份
echo "可用的备份文件:"
find "$BACKUP_DIR" -name "*.tar.gz" -type f -printf '%T@ %p\n' | sort -nr | cut -f2- -d" " | head -10

echo ""
read -p "请输入要恢复的备份文件名: " BACKUP_FILE

if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在"
    exit 1
fi

# 确认恢复
echo "即将恢复备份: $BACKUP_FILE"
read -p "确认恢复？(y/N): " CONFIRM

if [[ "$CONFIRM" != [yY] ]]; then
    echo "恢复已取消"
    exit 0
fi

# 停止应用程序服务
sudo systemctl stop qq-bot

# 创建恢复临时目录
TEMP_DIR="/tmp/restore_$(date +%s)"
mkdir -p "$TEMP_DIR"

# 解压备份
tar -xzf "$BACKUP_DIR/$BACKUP_FILE" -C "$TEMP_DIR"

# 恢复文件
cp -r "$TEMP_DIR/opt/qq-bot/data/trades" "$RESTORE_DIR/"
cp -r "$TEMP_DIR/opt/qq-bot/logs" "/opt/qq-bot/"

# 清理临时文件
rm -rf "$TEMP_DIR"

# 启动应用程序服务
sudo systemctl start qq-bot

echo "数据恢复完成"
EOF

sudo chmod +x /opt/qq-bot/scripts/restore_data.sh
```

## 8. 合规性和审计

### 数据访问审计

```bash
# 配置审计规则
sudo tee /etc/audit/rules.d/qq-bot-data.rules > /dev/null << EOF
# 监控数据文件访问
-w /opt/qq-bot/data/trades/trades.csv -p wa -k qqbot_trades
-w /opt/qq-bot/data/backups -p wa -k qqbot_backups
-w /opt/qq-bot/app/config.yaml -p wa -k qqbot_config
EOF

sudo systemctl restart auditd
```

这个配置方案确保了QQ交易机器人的数据存储安全、可靠且易于维护，同时提供了完整的备份和恢复机制。