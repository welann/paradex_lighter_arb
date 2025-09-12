#!/usr/bin/env python3
"""
对冲程序完整演示
展示从添加仓位到执行自动对冲的完整流程
"""

import asyncio
import time
from hedge_engine import HedgeEngine
from position_manager import PositionManager
from display_manager import DisplayManager

async def demo_hedge_system():
    """演示对冲系统完整功能"""
    print("🎬 对冲程序完整演示")
    print("=" * 60)
    
    # 创建实例
    pm = PositionManager()
    dm = DisplayManager()
    hedge_engine = HedgeEngine(hedge_threshold=0.05)  # 5%阈值
    
    print(f"\n🔧 系统配置:")
    print(f"   对冲阈值: {hedge_engine.hedge_threshold*100:.1f}%")
    
    # 1. 清空旧数据
    print(f"\n1️⃣ 清空旧数据...")
    pm.clear_all_positions()
    
    # 2. 添加初始仓位
    print(f"\n2️⃣ 添加初始仓位...")
    initial_positions = [
        ("SOL-USD-215-C", "sell", 1),
        ("BTC-USD-110000-C", "sell", 1),
    ]
    
    for symbol, side, quantity in initial_positions:
        print(f"   添加: {side} {quantity}张 {symbol}")
        pm.add_position(symbol, side, quantity)
        time.sleep(0.5)
    
    # 获取初始状态
    status = pm.get_position_status()
    initial_delta = status['delta_summary']
    
    print(f"\n📊 初始Delta状态:")
    for underlying, delta in initial_delta.items():
        print(f"   {underlying}: {delta:+.6f}")
    
    # 更新对冲引擎的缓存
    hedge_engine.update_position_cache(status['positions'], initial_delta)
    
    # 3. 添加更多仓位触发对冲条件
    print(f"\n3️⃣ 添加更多仓位 (将触发对冲)...")
    additional_positions = [
        ("SOL-USD-200-P", "buy", 2),   # 增加SOL敞口
        ("ETH-USD-4300-P", "buy", 3),  # 新增ETH敞口
    ]
    
    for symbol, side, quantity in additional_positions:
        print(f"   添加: {side} {quantity}张 {symbol}")
        pm.add_position(symbol, side, quantity)
        time.sleep(0.5)
    
    # 4. 获取新的状态
    new_status = pm.get_position_status()
    new_delta = new_status['delta_summary']
    
    print(f"\n📊 新的Delta状态:")
    for underlying, delta in new_delta.items():
        print(f"   {underlying}: {delta:+.6f}")
    
    # 5. 检查对冲需求
    print(f"\n4️⃣ 检查对冲需求...")
    recommendations = hedge_engine.check_hedge_requirement(new_delta)
    
    print(f"\n📋 对冲建议分析:")
    for rec in recommendations:
        status_symbol = "🚨" if rec.is_required else "💡"
        print(f"   {status_symbol} {rec.underlying}: Delta={rec.current_delta:+.6f}, "
              f"建议{rec.hedge_side} {rec.required_hedge_amount:.4f}, "
              f"价值=${rec.hedge_value:.2f}")
    
    # 6. 显示详细对冲界面
    print(f"\n5️⃣ 显示对冲确认界面...")
    print("\n" + "="*50)
    print("模拟用户确认流程:")
    print("="*50)
    
    # 显示建议但不执行（演示模式）
    should_hedge = hedge_engine.display_hedge_recommendations(recommendations)
    
    if should_hedge:
        print(f"\n✅ 用户确认执行对冲")
        
        # 注意：这里不实际下单，只是演示流程
        print(f"\n⚠️  演示模式：不会实际下单到Lighter")
        print(f"在实际使用中，系统将:")
        
        required_hedges = [r for r in recommendations if r.is_required]
        for rec in required_hedges:
            if rec.hedge_side != 'none':
                print(f"   • {rec.hedge_side.upper()} {rec.required_hedge_amount:.4f} {rec.underlying}")
                print(f"     预估价格: ${rec.current_price:.2f}")
                print(f"     交易价值: ${rec.hedge_value:.2f}")
    else:
        print(f"\n❌ 用户取消对冲")
    
    print(f"\n6️⃣ 完整状态展示...")
    dm.display_realtime_status()
    
    print(f"\n🎉 对冲程序演示完成!")
    print(f"\n💡 实际使用说明:")
    print(f"   1. 运行 'python hedge_cli.py' 启动交互式系统")
    print(f"   2. 使用 'add' 命令添加期权仓位")
    print(f"   3. 使用 'hedge check' 检查对冲需求")  
    print(f"   4. 使用 'hedge' 执行自动对冲")
    print(f"   5. 使用 'threshold 5' 设置5%对冲阈值")

def show_hedge_commands():
    """显示对冲相关命令"""
    print(f"\n📝 对冲功能命令:")
    print(f"=" * 40)
    
    commands = [
        ("hedge", "执行完整对冲流程(检查+确认+下单)"),
        ("hedge check", "仅检查对冲需求，不执行下单"),
        ("threshold", "查看当前对冲阈值"),
        ("threshold 5", "设置对冲阈值为5%"),
        ("threshold 10", "设置对冲阈值为10%"),
    ]
    
    for cmd, desc in commands:
        print(f"  {cmd:<15} - {desc}")

if __name__ == "__main__":
    try:
        asyncio.run(demo_hedge_system())
        show_hedge_commands()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  演示被中断")
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")