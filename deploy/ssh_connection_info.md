# QQ交易机器人服务器SSH连接信息

## 📋 服务器连接信息

### 生产环境服务器
```
服务器IP: [请在此处填写您的云服务器公网IP地址]
SSH端口: 22 (默认) 或 2222 (如果已修改)
用户名: qqbot 或 root (根据配置)
操作系统: Ubuntu 22.04 LTS
```

### 测试环境服务器 (可选)
```
服务器IP: [测试环境服务器IP]
SSH端口: 22
用户名: qqbot
操作系统: Ubuntu 22.04 LTS
```

## 🔑 SSH密钥信息

### SSH密钥对生成 (如果尚未生成)

如果您需要生成新的SSH密钥对，可以使用以下命令：

```bash
# 生成新的SSH密钥对 (RSA 4096位)
ssh-keygen -t rsa -b 4096 -C "qq-bot-production-$(date +%Y%m%d)" -f ~/.ssh/qq_bot_production

# 或者使用Ed25519算法 (更安全)
ssh-keygen -t ed25519 -C "qq-bot-production-$(date +%Y%m%d)" -f ~/.ssh/qq_bot_production_ed25519
```

### 公钥内容 (提供给AI)

请将以下公钥内容复制给AI使用：

```
[请在此处粘贴您的SSH公钥内容]

示例格式 (RSA):
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCw... user@hostname

示例格式 (Ed25519):
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@hostname
```

### 私钥保护说明

**重要**: 私钥文件 (`~/.ssh/qq_bot_production`) 必须严格保护，不要分享给任何人。

## 🔧 SSH连接命令

### 基本连接命令
```bash
# 使用密钥连接
ssh -i ~/.ssh/qq_bot_production qqbot@服务器IP

# 如果使用非默认端口
ssh -i ~/.ssh/qq_bot_production -p 2222 qqbot@服务器IP

# 使用Ed25519密钥
ssh -i ~/.ssh/qq_bot_production_ed25519 qqbot@服务器IP
```

### 高级连接选项
```bash
# 启用详细日志
ssh -v -i ~/.ssh/qq_bot_production qqbot@服务器IP

# 保持连接活跃
ssh -o ServerAliveInterval=60 -i ~/.ssh/qq_bot_production qqbot@服务器IP

# 禁用主机密钥检查 (仅用于测试)
ssh -o StrictHostKeyChecking=no -i ~/.ssh/qq_bot_production qqbot@服务器IP
```

## 📁 服务器目录结构

连接成功后，AI需要了解的关键目录：

```
/opt/qq-bot/          # 应用程序主目录
├── app/              # 应用程序代码
├── .venv/            # Python虚拟环境
├── scripts/          # 部署和管理脚本
├── data/             # 数据存储
└── logs/             # 日志文件

/var/log/qq-bot/      # 系统日志目录
```

## 🛡️ 安全配置说明

### 服务器端SSH配置
服务器已配置的安全设置：

```bash
# SSH服务配置 (通常位于 /etc/ssh/sshd_config)
Port 22 (或自定义端口)
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers qqbot
```

### 防火墙规则
```bash
# 允许的入站连接
ufw allow 22/tcp    # SSH
ufw allow 443/tcp  # HTTPS (如果适用)
```

## 🔄 自动化部署信息

### CI/CD集成
如果使用GitHub Actions自动化部署，需要配置以下secrets：

```yaml
# 在GitHub仓库的Settings > Secrets中配置
SERVER_IP: "您的服务器IP"
SERVER_USER: "qqbot"
SSH_PRIVATE_KEY: "您的SSH私钥内容"
```

### 部署脚本位置
```bash
# 主要部署脚本
/opt/qq-bot/scripts/deploy.sh

# 健康检查脚本
/opt/qq-bot/scripts/health_check.sh

# 监控脚本
/opt/qq-bot/scripts/dashboard.sh
```

## 🚨 故障排除

### 常见连接问题

1. **连接被拒绝**
   - 检查服务器IP是否正确
   - 确认SSH服务正在运行
   - 检查防火墙设置

2. **权限被拒绝**
   - 确认密钥文件权限: `chmod 600 ~/.ssh/qq_bot_production`
   - 确认公钥已添加到服务器的 `~/.ssh/authorized_keys`

3. **主机密钥验证失败**
   - 清除已知主机: `ssh-keygen -R 服务器IP`

### 日志检查
```bash
# 检查SSH连接日志
sudo tail -f /var/log/auth.log

# 检查应用程序日志
sudo tail -f /var/log/qq-bot/bot.log
```

## 📞 紧急联系方式

如果遇到连接问题，请联系：

- **运维团队**: [您的运维团队联系方式]
- **技术支持**: [技术支持联系方式]
- **紧急响应**: [24/7紧急联系方式]

---

**文档版本**: v1.0  
**最后更新**: 2026年4月15日  
**适用环境**: 生产环境  
**安全等级**: 机密 - 仅限授权人员访问