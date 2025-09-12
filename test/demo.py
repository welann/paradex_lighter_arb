#!/usr/bin/env python3
"""
期权对冲管理系统演示脚本
展示系统的完整功能
"""

from test.hedge_cli import HedgeCLI
from position_manager import PositionManager
from display_manager import DisplayManager
import time

def demo_system():
    """演示系统功能"""
    print("🎬 期权对冲管理系统演示")
    print("=" * 50)
    
    # 创建管理器实例
    pm = PositionManager()
    dm = DisplayManager()
    
    print("\n1️⃣ 清空旧数据...")
    pm.clear_all_positions()
    
    print("\n2️⃣ 添加测试仓位...")
    
    # 添加几个测试仓位
    test_positions = [
        ("SOL-USD-215-C", "sell", 2),
        ("SOL-USD-200-P", "buy", 1),
        ("BTC-USD-110000-C", "sell", 1),
        ("ETH-USD-4300-P", "buy", 3),
    ]
    
    for symbol, side, quantity in test_positions:
        print(f"   添加 {side} {quantity}张 {symbol}...")
        success = pm.add_position(symbol, side, quantity)
        if success:
            print(f"   ✅ 成功")
        else:
            print(f"   ❌ 失败")
        time.sleep(1)
    
    print("\n3️⃣ 显示当前仓位...")
    pm.show_positions()
    
    print("\n4️⃣ 显示仓位汇总和Delta分析...")
    pm.show_summary()
    
    print("\n5️⃣ 显示实时状态界面...")
    time.sleep(2)
    dm.display_realtime_status()
    
    print("\n6️⃣ 测试平仓功能...")
    print("   平仓1张SOL-USD-215-C...")
    pm.remove_position("SOL-USD-215-C", 1)
    
    print("\n7️⃣ 显示更新后的状态...")
    time.sleep(1)
    dm.display_realtime_status()
    
    print("\n🎉 演示完成!")
    print("💡 运行 'python hedge_cli.py' 开始交互式使用")

def show_command_examples():
    """显示命令示例"""
    print("\n📝 命令示例:")
    print("=" * 40)
    
    examples = [
        ("add sell sol-usd-215-c 2", "卖出2张SOL 215看涨期权"),
        ("add buy btc-usd-100000-p 1", "买入1张BTC 100000看跌期权"),
        ("delete sol-usd-215-c 1", "平仓1张SOL 215看涨期权"),
        ("show positions", "显示当前期权仓位"),
        ("show summary", "显示仓位汇总"),
        ("status", "显示实时Delta状态"),
        ("help", "显示帮助信息"),
        ("exit", "退出程序"),
    ]
    
    for cmd, desc in examples:
        print(f"  {cmd:<25} - {desc}")

if __name__ == "__main__":
    try:
        demo_system()
        show_command_examples()
    except KeyboardInterrupt:
        print("\n\n⚠️  演示被中断")
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")