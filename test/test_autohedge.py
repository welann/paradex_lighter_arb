#!/usr/bin/env python3
"""
测试自动对冲功能
演示开关自动对冲功能的完整流程
"""

from command_parser import CommandParser

def test_autohedge_commands():
    """测试自动对冲相关命令解析"""
    parser = CommandParser()
    
    print("🧪 测试自动对冲命令解析")
    print("=" * 50)
    
    test_commands = [
        "autohedge",
        "autohedge status", 
        "autohedge on",
        "autohedge off",
        "autohedge enable",
        "autohedge disable",
        "threshold",
        "threshold 3",
        "threshold 10",
        "threshold invalid"
    ]
    
    for cmd_text in test_commands:
        cmd = parser.parse(cmd_text)
        print(f"输入: {cmd_text}")
        print(f"解析: action={cmd.action}, operation={cmd.operation}")
        if cmd.params:
            print(f"参数: {cmd.params}")
        if cmd.action == 'error':
            print(f"错误: {cmd.params.get('message', '未知错误')}")
        print("-" * 30)

def demo_autohedge_workflow():
    """演示自动对冲工作流程"""
    print("\n🎬 自动对冲功能演示")
    print("=" * 50)
    
    print("💡 自动对冲功能说明:")
    print("   • 开启后，每次添加/删除期权仓位时会自动检查对冲需求")
    print("   • 根据设置的阈值判断是否需要对冲")
    print("   • 提供交互式确认，用户可选择执行或跳过")
    print("   • 支持实时开关和阈值调整")
    
    print(f"\n📋 新增的命令列表:")
    commands = [
        ("autohedge on", "开启自动对冲功能"),
        ("autohedge off", "关闭自动对冲功能"), 
        ("autohedge status", "查看自动对冲状态"),
        ("threshold 5", "设置对冲阈值为5%"),
        ("threshold", "查看当前阈值设置"),
    ]
    
    for cmd, desc in commands:
        print(f"   {cmd:<18} - {desc}")
    
    print(f"\n🔄 工作流程:")
    print(f"   1️⃣ autohedge on        # 开启自动对冲") 
    print(f"   2️⃣ threshold 3         # 设置3%阈值")
    print(f"   3️⃣ add sell sol-215-c 2 # 添加仓位")
    print(f"   4️⃣ 系统自动检查Delta变化")
    print(f"   5️⃣ 如超过阈值，提示执行对冲")
    print(f"   6️⃣ 用户确认后执行下单")
    
    print(f"\n⚙️  集成特性:")
    print(f"   • 状态显示: 实时显示自动对冲开关状态")
    print(f"   • 智能提醒: 仓位变动时自动触发检查")
    print(f"   • 交互确认: 用户可选择立即执行或稍后处理")
    print(f"   • 阈值管理: 支持动态调整对冲敏感度")

def show_usage_examples():
    """显示使用示例"""
    print(f"\n📖 使用示例场景")
    print("=" * 50)
    
    scenarios = [
        {
            "title": "🟢 开启自动对冲模式",
            "commands": [
                "autohedge on",
                "threshold 5", 
                "add sell sol-usd-215-c 3",
                "# 系统检测到Delta变化超过5%",
                "# 提示: 是否执行自动对冲? [yes/no/later]",
                "yes  # 确认执行对冲"
            ]
        },
        {
            "title": "🔴 手动对冲模式", 
            "commands": [
                "autohedge off",
                "add sell btc-usd-110000-c 1",
                "hedge check  # 手动检查对冲需求",
                "hedge        # 手动执行对冲"
            ]
        },
        {
            "title": "⚙️  配置管理",
            "commands": [
                "autohedge status    # 查看当前状态",
                "threshold           # 查看当前阈值", 
                "threshold 3         # 设置更敏感的阈值",
                "autohedge off       # 临时关闭自动对冲"
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['title']}:")
        print("-" * 40)
        for cmd in scenario['commands']:
            if cmd.startswith('#'):
                print(f"     {cmd}")
            else:
                print(f"   > {cmd}")

if __name__ == "__main__":
    try:
        test_autohedge_commands()
        demo_autohedge_workflow()
        show_usage_examples()
        
        print(f"\n✅ 自动对冲功能测试完成!")
        print(f"💡 运行 'python hedge_cli.py' 体验完整功能")
        
    except Exception as e:
        print(f"❌ 测试出错: {e}")