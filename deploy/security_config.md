# QQ交易机器人安全配置指南

## 1. 云服务商安全组配置

### 阿里云安全组配置

#### 入站规则
| 优先级 | 协议类型 | 端口范围 | 授权对象 | 描述 |
|--------|----------|----------|----------|------|
| 1 | 自定义TCP | 22/22 | 管理IP段 | SSH远程管理 |
| 2 | 自定义TCP | 443/443 | 0.0.0.0/0 | HTTPS访问 |
| 3 | 自定义TCP | 8080/8080 | 特定IP段 | 监控面板 |
| 100 | 全部 | -1/-1 | 0.0.0.0/0 | 拒绝所有其他入站 |

#### 出站规则
| 优先级 | 协议类型 | 端口范围 | 授权对象 | 描述 |
|--------|----------|----------|----------|------|
| 1 | 自定义TCP | 80/80 | 0.0.0.0/0 | HTTP API调用 |
| 2 | 自定义TCP | 443/443 | 0.0.0.0/0 | HTTPS API调用 |
| 3 | 自定义TCP | 9443/9443 | 交易所IP段 | Binance WebSocket |
| 4 | 全部 | -1/-1 | 0.0.0.0/0 | 允许所有出站 |

### 腾讯云安全组配置

#### 入站规则
```json
{
  "protocol": "TCP",
  "port": "22",
  "cidrBlock": "管理IP/32",
  "policy": "accept",
  "description": "SSH管理"
}
```

## 2. 系统级安全配置

### SSH安全加固

```bash
# 备份原始配置
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# 编辑SSH配置
sudo vim /etc/ssh/sshd_config
```

#### 推荐配置
```
# 更改默认端口
Port 2222

# 禁用root登录
PermitRootLogin no

# 禁用密码认证，使用密钥
PasswordAuthentication no
PubkeyAuthentication yes

# 限制用户登录
AllowUsers qqbot deployer

# 限制最大尝试次数
MaxAuthTries 3

# 配置空闲超时
ClientAliveInterval 300
ClientAliveCountMax 2

# 禁用不安全的认证方法
ChallengeResponseAuthentication no
UsePAM no

# 限制监听IP（如有多个网卡）
# ListenAddress 服务器内网IP
```

### 防火墙配置优化

```bash
# 清空现有规则
sudo ufw --force reset

# 配置默认策略
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 添加必要规则
sudo ufw allow 2222/tcp comment 'SSH管理端口'
sudo ufw allow 443/tcp comment 'HTTPS访问'

# 如有需要，添加应用程序端口
# sudo ufw allow 8080/tcp comment '监控面板'

# 启用防火墙
sudo ufw --force enable
```

## 3. 应用程序安全配置

### 环境变量安全

创建安全的环境变量文件：

```bash
# 创建生产环境配置文件
sudo -u qqbot tee /opt/qq-bot/.env.production > /dev/null << 'EOF'
# 敏感信息通过环境变量注入
BINANCE_API_KEY=${BINANCE_API_KEY}
BINANCE_SECRET_KEY=${BINANCE_SECRET_KEY}

# 应用程序配置
APP_ENV=production
LOG_LEVEL=INFO

# 网络配置
WEBSOCKET_TIMEOUT=30
API_RETRY_COUNT=3
EOF

# 设置严格权限
sudo chmod 600 /opt/qq-bot/.env.production
sudo chown qqbot:qqbot /opt/qq-bot/.env.production
```

### 密钥管理最佳实践

1. **使用密钥管理服务**
   - 阿里云KMS
   - 腾讯云密钥管理系统
   - AWS Secrets Manager

2. **环境分离**
   - 开发、测试、生产环境使用不同密钥
   - 定期轮换生产环境密钥

3. **访问控制**
   - 最小权限原则
   - 定期审计密钥使用情况

## 4. 网络安全配置

### VPN配置（可选）

对于高安全要求的部署，建议配置VPN：

```bash
# 安装WireGuard
sudo apt install -y wireguard

# 生成密钥对
wg genkey | sudo tee /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key

# 配置服务器端
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

### 网络监控

配置网络监控和入侵检测：

```bash
# 安装网络监控工具
sudo apt install -y nethogs iftop iptraf-ng

# 配置Suricata入侵检测
sudo apt install -y suricata
sudo systemctl enable suricata
sudo systemctl start suricata
```

## 5. 安全审计和监控

### 系统审计配置

```bash
# 安装审计工具
sudo apt install -y auditd

# 配置审计规则
sudo tee /etc/audit/rules.d/qq-bot.rules > /dev/null << EOF
# 监控敏感文件访问
-w /opt/qq-bot/.env -p wa -k qqbot_config
-w /opt/qq-bot/app/config.yaml -p wa -k qqbot_config

# 监控系统调用
-a always,exit -F arch=b64 -S connect -k network_connect
-a always,exit -F arch=b64 -S bind -k network_bind
EOF

sudo systemctl enable auditd
sudo systemctl start auditd
```

### 安全扫描脚本

创建定期安全扫描脚本：

```bash
sudo -u qqbot tee /opt/qq-bot/security_scan.sh > /dev/null << 'EOF'
#!/bin/bash

# QQ交易机器人安全扫描脚本

echo "=== 安全扫描报告 $(date) ==="

# 1. 检查系统更新
echo "1. 检查系统更新..."
apt list --upgradable 2>/dev/null | grep -v "Listing..." | wc -l

# 2. 检查失败登录尝试
echo "2. 检查失败登录..."
grep "Failed password" /var/log/auth.log | tail -5

# 3. 检查可疑进程
echo "3. 检查可疑进程..."
ps aux | grep -E "(miner|crypto|backdoor)" | grep -v grep

# 4. 检查网络连接
echo "4. 检查网络连接..."
netstat -tunlp | grep -v "127.0.0.1"

# 5. 检查文件权限
echo "5. 检查文件权限..."
find /opt/qq-bot -type f -perm /o=w -ls

echo "=== 扫描完成 ==="
EOF

sudo chmod +x /opt/qq-bot/security_scan.sh
```

## 6. 应急响应计划

### 安全事件响应流程

1. **检测阶段**
   - 监控告警触发
   - 确认安全事件

2. **响应阶段**
   - 隔离受影响系统
   - 收集证据
   - 通知相关人员

3. **恢复阶段**
   - 修复安全漏洞
   - 恢复系统运行
   - 更新安全策略

### 应急响应脚本

```bash
sudo tee /opt/qq-bot/emergency_response.sh > /dev/null << 'EOF'
#!/bin/bash

# 应急响应脚本

set -e

LOG_FILE="/var/log/qq-bot/security_incident.log"

log_incident() {
    echo "[$(date)] $1" >> "$LOG_FILE"
}

# 1. 停止应用程序服务
log_incident "停止应用程序服务..."
sudo systemctl stop qq-bot

# 2. 断开网络连接（可选）
# log_incident "断开网络连接..."
# sudo ufw --force enable
# sudo ufw deny 22/tcp
# sudo ufw deny 443/tcp

# 3. 备份当前状态
log_incident "备份当前状态..."
BACKUP_FILE="/opt/qq-bot/backups/emergency-$(date +%Y%m%d_%H%M%S).tar.gz"
sudo tar -czf "$BACKUP_FILE" /opt/qq-bot/app /var/log/qq-bot

# 4. 收集系统信息
log_incident "收集系统信息..."
{
    echo "=== 系统状态 ==="
    ps aux
    echo "=== 网络连接 ==="
    netstat -tunlp
    echo "=== 最近日志 ==="
    tail -100 /var/log/auth.log
    tail -100 /var/log/qq-bot/bot.log
} > "/opt/qq-bot/incident_report_$(date +%Y%m%d_%H%M%S).txt"

echo "应急响应完成，请检查日志文件: $LOG_FILE"
EOF

sudo chmod +x /opt/qq-bot/emergency_response.sh
```

## 7. 合规性和审计

### 安全合规检查清单

- [ ] 所有服务使用非默认端口
- [ ] 禁用不必要的系统服务
- [ ] 配置定期安全更新
- [ ] 启用系统审计日志
- [ ] 配置防火墙规则
- [ ] 使用密钥认证
- [ ] 定期备份重要数据
- [ ] 监控系统资源使用
- [ ] 定期安全扫描
- [ ] 制定应急响应计划

### 定期安全审计

建议每月执行一次完整的安全审计：

1. 系统漏洞扫描
2. 配置合规性检查
3. 日志分析
4. 权限审计
5. 备份完整性验证