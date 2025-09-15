#!/bin/bash

# Paradex Lighter Arbitrage Bot - One-Click Setup and Run Script
# 一键安装和运行脚本

set -e  # Exit on any error

echo "========================================="
echo "Paradex Lighter 套利机器人 - 一键启动脚本"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}[步骤] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[警告] $1${NC}"
}

print_error() {
    echo -e "${RED}[错误] $1${NC}"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_warning "检测到 .env.example 文件，但 .env 文件不存在"
        echo -n "是否要复制 .env.example 到 .env？ (y/n): "
        read -r answer
        if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
            cp .env.example .env
            print_step "已创建 .env 文件，请编辑该文件填写您的 API 信息"
            print_error "请先编辑 .env 文件填写 API 信息，然后重新运行此脚本"
            exit 1
        else
            print_error "需要 .env 文件才能运行程序，请手动创建"
            exit 1
        fi
    else
        print_error "未找到 .env 或 .env.example 文件"
        exit 1
    fi
fi

# Step 1: Install Git if not present
print_step "检查 Git..."
if ! command -v git &> /dev/null; then
    print_step "安装 Git..."
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y git
    elif command -v yum &> /dev/null; then
        sudo yum install -y git
    elif command -v brew &> /dev/null; then
        brew install git
    else
        print_error "无法自动安装 Git，请手动安装"
        exit 1
    fi
else
    echo "Git 已安装"
fi

# Step 2: Install Node.js and npm if not present
print_step "检查 Node.js 和 npm..."
if ! command -v npm &> /dev/null; then
    print_step "安装 npm..."
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y npm
    elif command -v yum &> /dev/null; then
        sudo yum install -y npm
    elif command -v brew &> /dev/null; then
        brew install npm
    else
        print_error "无法自动安装 npm，请手动安装 Node.js 和 npm"
        exit 1
    fi
else
    echo "npm 已安装"
fi

# Step 2: Install PM2 globally
print_step "检查并安装 PM2..."
if ! command -v pm2 &> /dev/null; then
    print_step "安装 PM2..."
    npm install -g pm2
else
    echo "PM2 已安装"
fi

# Step 4: Install Python UV if not present
print_step "检查并安装 UV..."
if ! command -v uv &> /dev/null; then
    print_step "使用官方安装脚本安装 UV..."
    # Use official installer (recommended method)
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add UV to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"

    # Verify installation
    if command -v uv &> /dev/null; then
        echo "UV 安装成功"
    else
        print_error "UV 安装失败，请检查网络连接或手动安装"
        exit 1
    fi
else
    echo "UV 已安装"
fi

# Step 5: Sync dependencies with UV
print_step "同步 Python 依赖..."
uv sync

# Step 6: Check if bot is already running
print_step "检查是否已有运行中的机器人..."
if pm2 list | grep -q "arb_bot"; then
    print_warning "检测到名为 'arb_bot' 的进程正在运行"
    echo -n "是否要重启该进程？ (y/n): "
    read -r restart_answer
    if [ "$restart_answer" = "y" ] || [ "$restart_answer" = "Y" ]; then
        pm2 restart arb_bot
    fi
else
    # Step 7: Start the bot with PM2
    print_step "启动套利机器人..."
    pm2 start "uv run python main.py" --name arb_bot
fi

# Step 8: Show PM2 status
print_step "显示 PM2 状态..."
pm2 status

echo ""
echo "========================================="
echo -e "${GREEN}设置完成！${NC}"
echo "========================================="
echo ""
echo "使用说明："
echo "1. 查看日志: pm2 logs arb_bot"
echo "2. 进入交互模式: pm2 attach (arb_bot的ID)"
echo "3. 停止程序: pm2 stop arb_bot"
echo "4. 重启程序: pm2 restart arb_bot"
echo "5. 删除程序: pm2 delete arb_bot"
echo ""
echo "进入交互模式后："
echo "- 输入 'help' 查看可用命令"
echo "- 按 Ctrl+C 退出交互模式"
echo ""

# Ask if user wants to attach to the process
echo -n "是否要立即进入交互模式？ (y/n): "
read -r attach_answer
if [ "$attach_answer" = "y" ] || [ "$attach_answer" = "Y" ]; then
    echo ""
    print_step "进入交互模式... (按 Ctrl+C 退出)"
    sleep 2
    # Get the process ID for arb_bot
    BOT_ID=$(pm2 list | grep "arb_bot" | awk '{print $2}' | head -1)
    if [ -n "$BOT_ID" ] && [ "$BOT_ID" != "│" ]; then
        pm2 attach $BOT_ID
    else
        print_error "无法找到 arb_bot 进程ID，请手动使用 'pm2 list' 查看进程ID，然后使用 'pm2 attach <ID>' 进入交互模式"
    fi
fi