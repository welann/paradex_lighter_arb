#!/usr/bin/env python3
"""
显示管理模块
实时展示仓位信息、Delta和价格数据
"""

import os
import time
from datetime import datetime
from typing import Dict, List
from position_manager import PositionManager


class DisplayManager:
    """显示管理器"""
    
    def __init__(self):
        self.position_manager = PositionManager()
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self, auto_hedge_enabled=False, hedge_threshold=0.05):
        """显示头部信息"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        auto_status = "🟢 ON" if auto_hedge_enabled else "🔴 OFF"
        
        print("=" * 80)
        print(f"🚀 期权对冲管理系统 - {current_time}")
        print(f"🤖 自动对冲: {auto_status} | 🎯 阈值: {hedge_threshold*100:.1f}%")
        print("=" * 80)
    
    def display_realtime_status(self, auto_hedge_enabled=False, hedge_threshold=0.05):
        """显示实时状态"""
        self.clear_screen()
        self.display_header(auto_hedge_enabled, hedge_threshold)
        
        try:
            status = self.position_manager.get_position_status()
            positions = status['positions']
            delta_summary = status['delta_summary']
            prices = status['prices']
            
            # 1. 显示市场价格
            self._display_market_prices(prices)
            
            # 2. 显示期权仓位
            self._display_option_positions(positions)
            
            # 3. 显示Delta汇总
            self._display_delta_summary(delta_summary, prices)
            
            # 4. 显示对冲建议
            self._display_hedge_suggestions(delta_summary, prices)
            
            print("\n" + "=" * 80)
            print("💡 输入 'help' 查看命令帮助，'exit' 退出程序")
            
        except Exception as e:
            print(f"❌ 显示状态时出错: {e}")
    
    def _display_market_prices(self, prices: Dict):
        """显示市场价格"""
        print(f"\n📊 实时价格:")
        print("-" * 50)
        
        if not prices:
            print("⚠️  无价格数据")
            return
        
        for symbol, data in prices.items():
            price = data.get('price', 0)
            change = data.get('change_24h', 0)
            change_color = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            
            print(f"{change_color} {symbol:<6} ${price:>10.2f} ({change:>+6.2f}%)")
    
    def _display_option_positions(self, positions: List):
        """显示期权仓位"""
        print(f"\n📝 期权仓位 ({len(positions)}个):")
        print("-" * 70)
        
        if not positions:
            print("   暂无活跃期权仓位")
            return
        
        print(f"{'期权代码':<20} {'方向':<6} {'数量':<6} {'Delta':<12} {'建仓时间':<12}")
        print("-" * 70)
        
        for pos in positions:
            try:
                delta = self.position_manager.paradex_api.get_option_delta(pos.symbol)
                delta_str = f"{delta:.4f}" if delta else "N/A"
                
                side_symbol = "🔴" if pos.side == "sell" else "🟢"
                entry_time = pos.entry_time[:10]  # 只显示日期
                
                print(f"{pos.symbol:<20} {side_symbol}{pos.side.upper():<5} {pos.quantity:<6} {delta_str:<12} {entry_time:<12}")
                
            except Exception as e:
                print(f"   {pos.symbol}: 显示错误 - {e}")
    
    def _display_delta_summary(self, delta_summary: Dict, prices: Dict):
        """显示Delta汇总"""
        print(f"\n⚖️  Delta敞口汇总:")
        print("-" * 60)
        
        if not delta_summary:
            print("   无Delta敞口")
            return
        
        total_delta_value = 0
        
        print(f"{'标的':<6} {'净Delta':<12} {'当前价格':<12} {'敞口价值':<12} {'状态'}")
        print("-" * 60)
        
        for underlying, net_delta in delta_summary.items():
            current_price = prices.get(underlying, {}).get('price', 0)
            delta_value = net_delta * current_price
            total_delta_value += delta_value
            
            # 判断风险状态
            if abs(net_delta) < 0.01:
                status = "✅ 平衡"
            elif abs(net_delta) < 0.1:
                status = "⚠️  小风险"
            else:
                status = "🚨 高风险"
            
            print(f"{underlying:<6} {net_delta:>+10.4f} ${current_price:>9.2f} ${delta_value:>+10.2f} {status}")
        
        print("-" * 60)
        print(f"{'总计':<6} {'':<12} {'':<12} ${total_delta_value:>+10.2f}")
    
    def _display_hedge_suggestions(self, delta_summary: Dict, prices: Dict):
        """显示对冲建议"""
        print(f"\n💡 对冲建议:")
        print("-" * 50)
        
        if not delta_summary:
            print("   无需对冲")
            return
        
        has_suggestions = False
        
        for underlying, net_delta in delta_summary.items():
            if abs(net_delta) >= 0.01:  # Delta敞口超过0.01才建议对冲
                has_suggestions = True
                current_price = prices.get(underlying, {}).get('price', 0)
                
                if net_delta > 0:
                    # 正Delta，建议卖出现货
                    action = "卖出"
                    quantity = abs(net_delta)
                else:
                    # 负Delta，建议买入现货
                    action = "买入"
                    quantity = abs(net_delta)
                
                hedge_value = quantity * current_price
                
                print(f"🎯 {underlying}: {action} {quantity:.4f} 份 (约${hedge_value:.2f})")
        
        if not has_suggestions:
            print("   ✅ Delta敞口较小，暂无对冲建议")
    
    def display_help(self):
        """显示帮助信息"""
        help_text = """
🆘 命令帮助
===========

📥 仓位管理:
  add sell sol-usd-215-c 2     - 卖出2张SOL 215看涨期权
  add buy btc-usd-100000-p 1   - 买入1张BTC 100000看跌期权
  delete sol-usd-215-c 1       - 平仓1张SOL 215看涨期权

📊 信息查看:
  show positions               - 显示期权仓位
  show orders                  - 显示对冲订单历史  
  show summary                 - 显示仓位汇总
  status                       - 刷新实时状态

🤖 自动对冲:
  autohedge on/off             - 开启/关闭自动对冲
  autohedge status             - 查看自动对冲状态
  threshold [数值]              - 设置对冲阈值(如threshold 3)

🔧 系统操作:
  clear                        - 清空所有仓位记录
  help                         - 显示此帮助
  exit/quit                    - 退出程序

📝 期权代码格式:
  [标的]-USD-[行权价]-[类型]
  
  标的: SOL, BTC, ETH, HYPE
  类型: C(看涨) P(看跌)
  
  示例: SOL-USD-215-C, BTC-USD-110000-P

💡 使用技巧:
  - 卖出期权会产生正Delta，需买入现货对冲
  - 买入期权会产生负Delta，需卖出现货对冲  
  - 系统会自动计算Delta敞口并给出对冲建议
"""
        print(help_text)
    
    def display_welcome(self):
        """显示欢迎信息"""
        print("""
🚀 期权对冲管理系统
==================

系统功能:
• 管理Paradex期权仓位
• 实时计算Delta敞口
• 提供对冲建议
• 记录交易历史

开始使用:
1. 输入 'add sell sol-usd-215-c 2' 添加期权仓位
2. 输入 'status' 查看实时Delta状态
3. 输入 'help' 查看完整命令列表

数据来源:
• 期权数据: Paradex API
• 现货价格: Lighter API
""")
    
    def display_positions_table(self):
        """显示仓位表格"""
        self.position_manager.show_positions()
    
    def display_summary_table(self):
        """显示汇总表格"""
        self.position_manager.show_summary()
    
    def display_orders_table(self):
        """显示订单表格"""
        self.position_manager.show_orders()


def test_display_manager():
    """测试显示管理器"""
    dm = DisplayManager()
    
    print("测试显示管理器...")
    
    # 添加一些测试仓位
    dm.position_manager.add_position("SOL-USD-215-C", "sell", 2)
    
    # 显示实时状态
    dm.display_realtime_status()
    
    print("\n按回车继续...")
    input()


if __name__ == "__main__":
    test_display_manager()