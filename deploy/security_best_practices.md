# QQ交易机器人安全最佳实践

## 1. 部署前安全准备

### 1.1 服务器安全基线

```bash
# 1. 系统更新和安全补丁
sudo apt update && sudo apt upgrade -y
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 2. 禁用不必要的服务
sudo systemctl disable --now apache2 nginx mysql mongodb

# 3. 配置自动安全更新
sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null << EOF
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESM:${distro_codename}";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "02:00";
EOF
```

### 1.2 网络安全配置

```bash
# 1. 配置防火墙（严格模式）
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 只允许必要的端口
sudo ufw allow 22/tcp comment 'SSH管理'
sudo ufw allow 443/tcp comment 'HTTPS访问'

# 启用防火墙
sudo ufw --force enable

# 2. 配置fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 配置SSH防护
sudo tee /etc/fail2ban/jail.d/sshd.conf > /dev/null << EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF
```

## 2. 应用程序安全配置

### 2.1 最小权限原则

```bash
# 创建专用应用程序用户
sudo useradd -r -s /bin/false -d /opt/qq-bot qqbot
sudo mkdir -p /opt/qq-bot /var/log/qq-bot
sudo chown qqbot:qqbot /opt/qq-bot /var/log/qq-bot
sudo chmod 750 /opt/qq-bot /var/log/qq-bot

# 配置文件权限
sudo chmod 600 /opt/qq-bot/.env
sudo chmod 640 /opt/qq-bot/app/config.yaml
```

### 2.2 敏感信息管理

```bash
# 使用环境变量存储敏感信息
sudo -u qqbot tee /opt/qq-bot/.env > /dev/null << 'EOF'
# 生产环境配置 - 通过CI/CD注入真实值
BINANCE_API_KEY=${BINANCE_API_KEY}
BINANCE_SECRET_KEY=${BINANCE_SECRET_KEY}

# 应用程序配置
APP_ENV=production
LOG_LEVEL=INFO

# 安全配置
API_RATE_LIMIT=10
WEBSOCKET_TIMEOUT=30
MAX_RETRY_ATTEMPTS=3
EOF

# 设置严格权限
sudo chmod 600 /opt/qq-bot/.env
sudo chown qqbot:qqbot /opt/qq-bot/.env
```

### 2.3 系统服务安全配置

```bash
# 创建安全的systemd服务
sudo tee /etc/systemd/system/qq-bot.service > /dev/null << EOF
[Unit]
Description=QQ Trading Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=qqbot
Group=qqbot
WorkingDirectory=/opt/qq-bot/app
EnvironmentFile=/opt/qq-bot/.env
ExecStart=/opt/qq-bot/start.sh
Restart=always
RestartSec=10

# 安全加固配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/qq-bot /var/log/qq-bot
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# 资源限制
MemoryLimit=1G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF
```

## 3. 网络安全最佳实践

### 3.1 VPN和网络隔离

```bash
# 配置WireGuard VPN（可选）
sudo apt install -y wireguard

# 生成密钥
wg genkey | sudo tee /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key
sudo chmod 600 /etc/wireguard/private.key

# 配置服务器
sudo tee /etc/wireguard/wg0.conf > /dev/null << EOF
[Interface]
PrivateKey = $(sudo cat /etc/wireguard/private.key)
Address = 10.0.0.1/24
ListenPort = 51820
SaveConfig = true

# 客户端配置
[Peer]
PublicKey = 客户端公钥
AllowedIPs = 10.0.0.2/32
EOF
```

### 3.2 网络监控和入侵检测

```bash
# 安装网络监控工具
sudo apt install -y tcpdump nmap iptables-persistent

# 配置iptables规则
sudo iptables -A INPUT -p tcp --dport 22 -m recent --name ssh --set
sudo iptables -A INPUT -p tcp --dport 22 -m recent --name ssh --update --seconds 60 --hitcount 4 -j DROP

# 保存iptables规则
sudo netfilter-persistent save
```

## 4. 数据安全配置

### 4.1 加密和数据保护

```bash
# 配置数据加密（如果需要）
sudo apt install -y ecryptfs-utils

# 创建加密目录
sudo mkdir /opt/qq-bot/encrypted_data
sudo mount -t ecryptfs /opt/qq-bot/encrypted_data /opt/qq-bot/encrypted_data
```

### 4.2 备份安全

```bash
# 创建安全的备份脚本
sudo -u qqbot tee /opt/qq-bot/scripts/secure_backup.sh > /dev/null << 'EOF'
#!/bin/bash

# 安全备份脚本
set -e

BACKUP_DIR="/opt/qq-bot/backups"
ENCRYPT_KEY="备份加密密钥"  # 从安全存储获取
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份
tar -czf - /opt/qq-bot/app /var/log/qq-bot | \
    openssl enc -aes-256-cbc -salt -pass pass:"$ENCRYPT_KEY" \
    -out "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz.enc"

# 验证备份
if openssl enc -d -aes-256-cbc -pass pass:"$ENCRYPT_KEY" \
    -in "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz.enc" | tar -tzf - > /dev/null; then
    echo "备份验证成功"
else
    echo "备份验证失败"
    exit 1
fi

# 清理旧备份
find "$BACKUP_DIR" -name "*.enc" -mtime +30 -delete
EOF

sudo chmod 700 /opt/qq-bot/scripts/secure_backup.sh
```

## 5. 审计和合规性

### 5.1 系统审计配置

```bash
# 安装审计工具
sudo apt install -y auditd

# 配置审计规则
sudo tee /etc/audit/rules.d/qq-bot.rules > /dev/null << EOF
# 监控应用程序文件访问
-w /opt/qq-bot/app -p wa -k qqbot_app
-w /opt/qq-bot/.env -p wa -k qqbot_config
-w /var/log/qq-bot -p wa -k qqbot_logs

# 监控系统调用
-a always,exit -F arch=b64 -S connect -k network_connect
-a always,exit -F arch=b64 -S bind -k network_bind
-a always,exit -F arch=b64 -S execve -k process_exec
EOF

sudo systemctl enable auditd
sudo systemctl start auditd
```

### 5.2 安全扫描和漏洞评估

```bash
# 安装安全扫描工具
sudo apt install -lynis

# 运行安全扫描
sudo lynis audit system

# 安装漏洞扫描工具
sudo apt install -y openscap-scanner

# 下载安全基线
wget https://static.open-scap.org/ssg-content/ssg-ubuntu2204-ds.xml

# 运行合规性检查
sudo oscap xccdf eval --profile xccdf_org.ssgproject.content_profile_standard \
    --results scan-results.xml \
    --report scan-report.html \
    ssg-ubuntu2204-ds.xml
```

## 6. 应急响应计划

### 6.1 安全事件响应

```bash
# 创建应急响应脚本
sudo tee /opt/qq-bot/scripts/emergency_response.sh > /dev/null << 'EOF'
#!/bin/bash

# 应急响应脚本
set -e

LOG_FILE="/var/log/qq-bot/security_incident.log"

log_incident() {
    echo "[$(date)] $1" >> "$LOG_FILE"
    logger -t qqbot-incident "$1"
}

# 1. 立即停止服务
log_incident "停止应用程序服务..."
sudo systemctl stop qq-bot

# 2. 隔离网络（可选）
# log_incident "隔离网络连接..."
# sudo ufw deny 22/tcp
# sudo ufw deny 443/tcp

# 3. 收集证据
log_incident "收集系统证据..."
INCIDENT_DIR="/opt/qq-bot/incident_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$INCIDENT_DIR"

# 收集系统信息
ps aux > "$INCIDENT_DIR/processes.txt"
netstat -tunlp > "$INCIDENT_DIR/network.txt"
last > "$INCIDENT_DIR/logins.txt"

# 收集应用程序日志
cp -r /var/log/qq-bot "$INCIDENT_DIR/"
cp /opt/qq-bot/app/config.yaml "$INCIDENT_DIR/"

# 4. 备份当前状态
log_incident "创建紧急备份..."
sudo -u qqbot tar -czf "$INCIDENT_DIR/emergency_backup.tar.gz" /opt/qq-bot/app

# 5. 通知相关人员
log_incident "发送安全警报..."
# 这里可以集成邮件、短信、Slack等通知方式

echo "应急响应完成，证据保存在: $INCIDENT_DIR"
EOF

sudo chmod 700 /opt/qq-bot/scripts/emergency_response.sh
```

### 6.2 恢复和修复流程

```bash
# 创建恢复脚本
sudo tee /opt/qq-bot/scripts/recovery_procedure.sh > /dev/null << 'EOF'
#!/bin/bash

# 安全事件恢复流程
set -e

echo "=== 安全事件恢复流程 ==="

# 1. 验证系统完整性
echo "1. 验证系统完整性..."
rpm -Va  # 对于RPM系统
dpkg --verify  # 对于Debian系统

# 2. 检查后门和恶意软件
echo "2. 检查恶意软件..."
sudo apt install -y chkrootkit rkhunter
sudo chkrootkit
sudo rkhunter --check

# 3. 更新系统和应用程序
echo "3. 更新系统..."
sudo apt update && sudo apt upgrade -y

# 4. 重置所有密码和密钥
echo "4. 重置安全凭证..."
# 重置应用程序API密钥
# 重置系统用户密码
# 重新生成SSH密钥

# 5. 从干净备份恢复
echo "5. 从备份恢复..."
# 使用最近的干净备份恢复数据

# 6. 重新部署应用程序
echo "6. 重新部署应用程序..."
# 从版本控制重新部署代码

# 7. 验证恢复结果
echo "7. 验证恢复..."
sudo /opt/qq-bot/scripts/health_check.sh
sudo /opt/qq-bot/scripts/security_scan.sh

echo "恢复流程完成"
EOF

sudo chmod 700 /opt/qq-bot/scripts/recovery_procedure.sh
```

## 7. 持续安全监控

### 7.1 安全监控配置

```bash
# 创建安全监控脚本
sudo -u qqbot tee /opt/qq-bot/scripts/security_monitor.sh > /dev/null << 'EOF'
#!/bin/bash

# 安全监控脚本
set -e

SECURITY_LOG="/var/log/qq-bot/security.log"

# 检查失败登录尝试
FAILED_LOGINS=$(grep "Failed password" /var/log/auth.log | wc -l)
if [ "$FAILED_LOGINS" -gt 10 ]; then
    echo "$(date): 高失败登录次数: $FAILED_LOGINS" >> "$SECURITY_LOG"
fi

# 检查可疑进程
SUSPICIOUS_PROCS=$(ps aux | grep -E "(miner|backdoor|exploit)" | grep -v grep | wc -l)
if [ "$SUSPICIOUS_PROCS" -gt 0 ]; then
    echo "$(date): 发现可疑进程" >> "$SECURITY_LOG"
fi

# 检查文件完整性
if [ -f "/opt/qq-bot/app/main.py" ]; then
    FILE_HASH=$(sha256sum /opt/qq-bot/app/main.py | cut -d' ' -f1)
    KNOWN_HASH="已知的文件哈希值"  # 应该从安全存储获取
    
    if [ "$FILE_HASH" != "$KNOWN_HASH" ]; then
        echo "$(date): 应用程序文件被修改" >> "$SECURITY_LOG"
    fi
fi

# 检查网络连接
SUSPICIOUS_CONNS=$(netstat -tunlp | grep -v "127.0.0.1" | grep -v "::1" | wc -l)
if [ "$SUSPICIOUS_CONNS" -gt 20 ]; then
    echo "$(date): 异常网络连接数量: $SUSPICIOUS_CONNS" >> "$SECURITY_LOG"
fi
EOF

sudo chmod 700 /opt/qq-bot/scripts/security_monitor.sh

# 添加到crontab
sudo -u qqbot crontab -l | { cat; echo "*/5 * * * * /opt/qq-bot/scripts/security_monitor.sh > /dev/null 2>&1"; } | sudo -u qqbot crontab -
```

## 8. 合规性检查清单

### 安全合规检查清单

- [ ] 系统已安装所有安全补丁
- [ ] 防火墙配置正确
- [ ] SSH安全配置完成
- [ ] 应用程序使用专用用户运行
- [ ] 敏感信息通过环境变量管理
- [ ] 文件权限设置正确
- [ ] 备份策略实施
- [ ] 监控系统配置
- [ ] 应急响应计划准备
- [ ] 安全审计启用
- [ ] 定期安全扫描计划
- [ ] 员工安全培训完成

### 定期安全审计

建议每月执行一次完整的安全审计：
1. 系统漏洞扫描
2. 配置合规性检查
3. 日志分析
4. 权限审计
5. 备份完整性验证
6. 应急响应演练

这个安全最佳实践指南确保了QQ交易机器人在云服务器环境中的安全部署和运行，符合企业级安全标准。