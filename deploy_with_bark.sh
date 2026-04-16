#!/usr/bin/expect -f

# ================================================================================
# QQ Trading Bot 自动部署脚本（密码认证）- 带 Bark 通知
# ================================================================================

# 配置
set server_ip "43.156.54.113"
set server_port "22"
set server_user "root"
set server_password "Junhao@2026"
set remote_dir "/root/qq"
set local_package "/tmp/qq_bot_deploy.tar.gz"

# 超时时间
set timeout 60

# 创建项目压缩包
puts "\033\[0;34m\[INFO\]\033\[0m 创建项目压缩包..."
catch {exec env COPYFILE_DISABLE=1 tar -czf $local_package --exclude ".venv" --exclude "__pycache__" --exclude "*.pyc" --exclude ".git" --exclude "logs" --exclude "*.swp" --exclude "*.log" --exclude ".DS_Store" --exclude "._*" -C [file dirname [info script]] .} result
puts "\033\[0;32m\[SUCCESS\]\033\[0m 项目已打包：$local_package"

# 测试 SSH 连接
puts "\033\[0;34m\[INFO\]\033\[0m 测试 SSH 连接..."
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p $server_port $server_user@$server_ip "echo '连接成功'"
expect {
    "password:" {
        send "$server_password\r"
        expect {
            "连接成功" { puts "\033\[0;32m\[SUCCESS\]\033\[0m SSH 连接测试成功" }
            timeout { puts "\033\[0;31m\[ERROR\]\033\[0m SSH 连接超时"; exit 1 }
        }
    }
    timeout { puts "\033\[0;31m\[ERROR\]\033\[0m SSH 连接超时"; exit 1 }
}

# 上传文件
puts "\033\[0;34m\[INFO\]\033\[0m 上传文件到服务器..."
spawn scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 -P $server_port $local_package $server_user@$server_ip:/tmp/
expect {
    "password:" {
        send "$server_password\r"
        expect eof
        puts "\033\[0;32m\[SUCCESS\]\033\[0m 文件上传成功"
    }
    timeout { puts "\033\[0;31m\[ERROR\]\033\[0m 上传超时"; exit 1 }
}

# 远程部署
puts "\033\[0;34m\[INFO\]\033\[0m 执行远程部署..."
spawn ssh -o StrictHostKeyChecking=no -p $server_port $server_user@$server_ip
expect {
    "password:" {
        send "$server_password\r"
        expect {
            -re "#|\\$" {
                send "cd /tmp && rm -rf /root/qq 2>/dev/null\r"
                expect -re "#|\\$"
                
                send "mkdir -p qq_temp && tar -xzf qq_bot_deploy.tar.gz -C qq_temp\r"
                expect -re "#|\\$"
                
                send "mv qq_temp /root/qq\r"
                expect -re "#|\\$"
                
                send "echo '解压完成' && ls -la /root/qq/ | head -20\r"
                expect -re "#|\\$"
                
                send "cd /root/qq && python3 -m venv .venv\r"
                expect -re "#|\\$"
                
                send "source .venv/bin/activate && pip install --upgrade pip\r"
                expect -re "#|\\$"
                
                send "pip install -r requirements.txt\r"
                expect -re "#|\\$"
                
                send "mkdir -p logs\r"
                expect -re "#|\\$"
                
                send "echo '部署完成！'\r"
                expect -re "#|\\$"
                
                send "exit\r"
                expect eof
                
                puts "\033\[0;32m\[SUCCESS\]\033\[0m 远程部署完成"
            }
        }
    }
    timeout { puts "\033\[0;31m\[ERROR\]\033\[0m SSH 登录超时"; exit 1 }
}

# 启动服务
puts "\033\[0;34m\[INFO\]\033\[0m 启动服务..."
spawn ssh -o StrictHostKeyChecking=no -p $server_port $server_user@$server_ip
expect {
    "password:" {
        send "$server_password\r"
        expect {
            -re "#|\\$" {
                send "cd /root/qq\r"
                expect -re "#|\\$"
                
                send "source .venv/bin/activate\r"
                expect -re "#|\\$"
                
                send "screen -S qq_bot -X quit 2>/dev/null || true\r"
                expect -re "#|\\$"
                
                send "sleep 2\r"
                expect -re "#|\\$"
                
                send "screen -dmS qq_bot python3 main.py\r"
                expect -re "#|\\$"
                
                send "sleep 3\r"
                expect -re "#|\\$"
                
                send "screen -list | grep -q qq_bot && echo '服务已成功启动！' || echo '服务启动失败'\r"
                expect -re "#|\\$"
                
                send "exit\r"
                expect eof
                
                puts "\033\[0;32m\[SUCCESS\]\033\[0m 服务已启动"
            }
        }
    }
    timeout { puts "\033\[0;31m\[ERROR\]\033\[0m SSH 登录超时"; exit 1 }
}

# 清理
puts "\033\[0;34m\[INFO\]\033\[0m 清理临时文件..."
catch {exec rm -f $local_package}
puts "\033\[0;32m\[SUCCESS\]\033\[0m 清理完成"

puts ""
puts "============================================================"
puts "\033\[0;32m\[SUCCESS\]\033\[0m 部署全部完成！"
puts "============================================================"
puts ""
puts "📱 Bark 通知功能已启用，您将会收到："
puts "  ✅ 系统启动通知"
puts "  ⚠️  错误报警通知"
puts "  💰 交易平仓通知"
puts "  🎯 交易信号通知"
puts ""
puts "后续操作："
puts "  1. 查看日志：ssh -p $server_port $server_user@$server_ip 'screen -r qq_bot'"
puts "  2. 停止服务：ssh -p $server_port $server_user@$server_ip 'screen -S qq_bot -X quit'"
puts ""
