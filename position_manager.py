#!/usr/bin/env python3
"""
仓位管理模块
管理期权仓位和对冲操作
"""

from typing import Dict, List, Optional, Tuple
from database import DatabaseManager, OptionPosition, HedgeOrder
from paradex_market import ParadexAPI
from lighter_market import LighterMarketAPI
from datetime import datetime


class PositionManager:
    """仓位管理器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.paradex_api = ParadexAPI()
        self.lighter_api = LighterMarketAPI()
        
        # 标的资产映射 (期权标的 -> 现货)
        self.underlying_mapping = {
            'SOL': 'SOL',
            'BTC': 'BTC',
            'ETH': 'ETH',
            'HYPE': 'HYPE'
        }
    
    def add_position(self, symbol: str, side: str, quantity: int) -> bool:
        """
        添加期权仓位
        
        Args:
            symbol: 期权代码 (如 SOL-USD-215-C)
            side: 方向 ('buy' or 'sell')
            quantity: 数量
            
        Returns:
            bool: 是否成功
        """
        print(f"添加期权仓位: {side.upper()} {quantity}张 {symbol}")
        
        # 添加到数据库
        success = self.db.add_option_position(symbol, side, quantity)
        
        if success:
            print(f"✅ 成功添加期权仓位")
            
            # 计算是否需要对冲
            self._suggest_hedge(symbol, side, quantity)
            
            return True
        else:
            print(f"❌ 添加期权仓位失败")
            return False
    
    def remove_position(self, symbol: str, quantity: int) -> bool:
        """
        平仓期权仓位
        
        Args:
            symbol: 期权代码
            quantity: 平仓数量
            
        Returns:
            bool: 是否成功
        """
        print(f"平仓期权仓位: {quantity}张 {symbol}")
        
        success = self.db.delete_option_position(symbol, quantity)
        
        if success:
            print(f"✅ 成功平仓期权仓位")
            return True
        else:
            print(f"❌ 平仓期权仓位失败")
            return False
    
    def _suggest_hedge(self, symbol: str, side: str, quantity: int):
        """
        建议对冲操作
        
        Args:
            symbol: 期权代码
            side: 期权方向
            quantity: 期权数量
        """
        try:
            # 获取期权delta
            delta = self.paradex_api.get_option_delta(symbol)
            if delta is None:
                print("⚠️  无法获取期权Delta，请手动计算对冲")
                return
            
            # 提取标的资产
            underlying = symbol.split('-')[0]
            
            # 计算对冲数量
            # 卖出期权需要买入现货对冲，买入期权需要卖出现货对冲
            hedge_delta = delta * quantity
            if side == 'sell':
                hedge_side = 'buy'
                hedge_quantity = abs(hedge_delta)
            else:
                hedge_side = 'sell' 
                hedge_quantity = abs(hedge_delta)
            
            # 获取当前价格
            market_data = self.lighter_api.get_market_by_symbol(underlying)
            current_price = market_data.last_trade_price if market_data else 0
            
            print(f"\n💡 对冲建议:")
            print(f"   期权Delta: {delta:.6f}")
            print(f"   总Delta敞口: {hedge_delta:.6f}")
            print(f"   建议对冲: {hedge_side.upper()} {hedge_quantity:.4f} {underlying}")
            print(f"   当前{underlying}价格: ${current_price:.2f}")
            print(f"   对冲价值约: ${hedge_quantity * current_price:.2f}")
            
        except Exception as e:
            print(f"⚠️  计算对冲建议时出错: {e}")
    
    def calculate_total_delta(self) -> Dict[str, float]:
        """
        计算总Delta敞口
        
        Returns:
            Dict[str, float]: 每个标的资产的总Delta
        """
        positions = self.db.get_active_option_positions()
        delta_summary = {}
        
        for pos in positions:
            try:
                # 获取期权delta
                delta = self.paradex_api.get_option_delta(pos.symbol)
                if delta is None:
                    continue
                
                # 提取标的资产
                underlying = pos.symbol.split('-')[0]
                
                if underlying not in delta_summary:
                    delta_summary[underlying] = 0
                
                # 计算总delta (考虑买卖方向)
                position_delta = delta * pos.quantity
                if pos.side == 'sell':
                    position_delta = -position_delta
                
                delta_summary[underlying] += position_delta
                
            except Exception as e:
                print(f"计算{pos.symbol} Delta时出错: {e}")
                continue
        
        return delta_summary
    
    def get_position_status(self) -> Dict:
        """
        获取仓位状态
        
        Returns:
            Dict: 包含仓位信息和Delta信息的字典
        """
        # 获取期权仓位
        positions = self.db.get_active_option_positions()
        summary = self.db.get_position_summary()
        
        # 计算Delta
        delta_summary = self.calculate_total_delta()
        
        # 获取最新价格
        prices = {}
        for underlying in self.underlying_mapping.keys():
            try:
                market_data = self.lighter_api.get_market_by_symbol(underlying)
                if market_data:
                    prices[underlying] = {
                        'price': market_data.last_trade_price,
                        'change_24h': market_data.daily_price_change
                    }
            except:
                prices[underlying] = {'price': 0, 'change_24h': 0}
        
        return {
            'positions': positions,
            'summary': summary,
            'delta_summary': delta_summary,
            'prices': prices,
            'timestamp': datetime.now().isoformat()
        }
    
    def show_positions(self):
        """显示当前仓位"""
        status = self.get_position_status()
        positions = status['positions']
        
        if not positions:
            print("📝 当前没有活跃的期权仓位")
            return
        
        print(f"\n📊 当前期权仓位 ({len(positions)}个):")
        print("-" * 80)
        print(f"{'序号':<4} {'期权代码':<20} {'方向':<6} {'数量':<8} {'Delta':<12} {'建仓时间':<20}")
        print("-" * 80)
        
        for i, pos in enumerate(positions, 1):
            delta = self.paradex_api.get_option_delta(pos.symbol)
            delta_str = f"{delta:.6f}" if delta else "N/A"
            
            print(f"{i:<4} {pos.symbol:<20} {pos.side.upper():<6} {pos.quantity:<8} {delta_str:<12} {pos.entry_time[:19]}")
    
    def show_summary(self):
        """显示仓位汇总"""
        status = self.get_position_status()
        summary = status['summary']
        delta_summary = status['delta_summary']
        prices = status['prices']
        
        if not summary:
            print("📝 当前没有仓位汇总")
            return
        
        print(f"\n📈 仓位与Delta汇总:")
        print("=" * 70)
        
        for underlying, data in summary.items():
            current_price = prices.get(underlying, {}).get('price', 0)
            change_24h = prices.get(underlying, {}).get('change_24h', 0)
            total_delta = delta_summary.get(underlying, 0)
            
            print(f"\n🪙 {underlying}:")
            print(f"   当前价格: ${current_price:.2f} ({change_24h:+.2f}%)")
            print(f"   多头仓位: {data['total_long']}张")
            print(f"   空头仓位: {data['total_short']}张")
            print(f"   净Delta敞口: {total_delta:.6f}")
            print(f"   Delta价值: ${total_delta * current_price:.2f}")
            
            # 详细仓位列表
            if data['long_positions']:
                print(f"   多头明细:")
                for pos in data['long_positions']:
                    delta = self.paradex_api.get_option_delta(pos.symbol)
                    print(f"     {pos.symbol} {pos.quantity}张 (Delta: {delta:.6f})")
            
            if data['short_positions']:
                print(f"   空头明细:")
                for pos in data['short_positions']:
                    delta = self.paradex_api.get_option_delta(pos.symbol)
                    print(f"     {pos.symbol} {pos.quantity}张 (Delta: {delta:.6f})")
    
    def show_orders(self, limit: int = 20):
        """显示对冲订单历史"""
        orders = self.db.get_hedge_orders(limit)
        
        if not orders:
            print("📝 暂无对冲订单记录")
            return
        
        print(f"\n📋 对冲订单历史 (最近{len(orders)}条):")
        print("-" * 90)
        print(f"{'序号':<4} {'平台':<8} {'币种':<6} {'方向':<6} {'数量':<12} {'价格':<12} {'时间':<20}")
        print("-" * 90)
        
        for i, order in enumerate(orders, 1):
            print(f"{i:<4} {order.platform:<8} {order.symbol:<6} {order.side.upper():<6} "
                  f"{order.quantity:<12.4f} ${order.price:<11.2f} {order.order_time[:19]}")
    
    def clear_all_positions(self):
        """清空所有仓位"""
        self.db.clear_all_positions()
        print("🗑️  已清空所有仓位记录")


def test_position_manager():
    """测试仓位管理器"""
    pm = PositionManager()
    
    print("测试仓位管理器...")
    
    # 测试添加仓位
    pm.add_position("SOL-USD-215-C", "sell", 2)
    pm.add_position("SOL-USD-200-P", "buy", 1)
    
    # 显示仓位
    pm.show_positions()
    pm.show_summary()
    
    print("\n测试完成!")


if __name__ == "__main__":
    test_position_manager()