#!/usr/bin/env python3
"""
对冲引擎模块
实现自动对冲逻辑，包括阈值检查、确认机制和下单执行
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from database import DatabaseManager
from paradex_market import ParadexAPI
from lighter_market import LighterMarketAPI
from lighter_trading import LighterTrader


@dataclass
class HedgeRecommendation:
    """对冲建议数据类"""
    underlying: str
    current_delta: float
    required_hedge_amount: float
    hedge_side: str  # 'buy' or 'sell'
    current_price: float
    hedge_value: float
    is_required: bool  # 是否需要对冲


@dataclass
class HedgeResult:
    """对冲执行结果"""
    success: bool
    underlying: str
    side: str
    amount: float
    price: float
    tx_hash: Optional[str] = None
    error_message: Optional[str] = None


class HedgeEngine:
    """对冲引擎"""
    
    def __init__(self, hedge_threshold: float = 0.05):
        """
        初始化对冲引擎
        
        Args:
            hedge_threshold: 对冲阈值，默认5%
        """
        self.db = DatabaseManager()
        self.paradex_api = ParadexAPI()
        self.lighter_api = LighterMarketAPI()
        self.lighter_trader = LighterTrader()
        
        self.hedge_threshold = hedge_threshold
        
        # 记录上次的仓位状态
        self.last_positions = {}
        self.last_delta_summary = {}
    
    def check_hedge_requirement(self, current_delta_summary: Dict[str, float]) -> List[HedgeRecommendation]:
        """
        检查是否需要对冲
        
        Args:
            current_delta_summary: 当前Delta汇总
            
        Returns:
            List[HedgeRecommendation]: 对冲建议列表
        """
        recommendations = []
        
        for underlying, current_delta in current_delta_summary.items():
            # 获取上次的Delta值
            last_delta = self.last_delta_summary.get(underlying, 0.0)
            
            # 计算Delta变化百分比
            if abs(last_delta) > 0.0001:  # 避免除以接近0的数
                delta_change_pct = abs(current_delta - last_delta) / abs(last_delta)
            else:
                # 如果上次Delta接近0，使用绝对变化
                delta_change_pct = abs(current_delta) if abs(current_delta) > 0.0001 else 0
            
            # 判断是否需要对冲
            is_required = delta_change_pct >= self.hedge_threshold or abs(current_delta) >= 0.1
            
            if is_required or abs(current_delta) > 0.001:  # 总是生成建议，但标记是否必需
                try:
                    # 获取当前价格
                    market_data = self.lighter_api.get_market_by_symbol(underlying)
                    current_price = market_data.last_trade_price if market_data else 0
                    
                    # 确定对冲方向和数量
                    if current_delta > 0:
                        # 正Delta，需要卖出现货
                        hedge_side = 'sell'
                        required_amount = abs(current_delta)
                    elif current_delta < 0:
                        # 负Delta，需要买入现货
                        hedge_side = 'buy'
                        required_amount = abs(current_delta)
                    else:
                        # Delta为0，无需对冲
                        hedge_side = 'none'
                        required_amount = 0
                    
                    hedge_value = required_amount * current_price
                    
                    recommendations.append(HedgeRecommendation(
                        underlying=underlying,
                        current_delta=current_delta,
                        required_hedge_amount=required_amount,
                        hedge_side=hedge_side,
                        current_price=current_price,
                        hedge_value=hedge_value,
                        is_required=is_required
                    ))
                    
                except Exception as e:
                    print(f"⚠️  获取{underlying}对冲建议时出错: {e}")
        
        return recommendations
    
    def display_hedge_recommendations(self, recommendations: List[HedgeRecommendation]) -> bool:
        """
        显示对冲建议并询问用户确认
        
        Args:
            recommendations: 对冲建议列表
            
        Returns:
            bool: 用户是否确认执行对冲
        """
        if not recommendations:
            print("✅ 当前无需对冲")
            return False
        
        print("\n" + "=" * 70)
        print("🎯 对冲建议分析")
        print("=" * 70)
        
        required_hedges = [r for r in recommendations if r.is_required]
        optional_hedges = [r for r in recommendations if not r.is_required]
        
        if required_hedges:
            print(f"\n🚨 需要立即对冲的仓位 (超过{self.hedge_threshold*100:.1f}%阈值):")
            print("-" * 70)
            print(f"{'标的':<6} {'当前Delta':<12} {'对冲方向':<8} {'数量':<12} {'当前价格':<10} {'对冲价值':<10}")
            print("-" * 70)
            
            total_required_value = 0
            for rec in required_hedges:
                if rec.hedge_side != 'none':
                    total_required_value += rec.hedge_value
                    print(f"{rec.underlying:<6} {rec.current_delta:>+10.4f} {rec.hedge_side.upper():<8} "
                          f"{rec.required_hedge_amount:<10.4f} ${rec.current_price:<9.2f} ${rec.hedge_value:<9.2f}")
            
            print("-" * 70)
            print(f"必需对冲总价值: ${total_required_value:.2f}")
        
        if optional_hedges:
            print(f"\n💡 可选对冲建议 (低于阈值，可考虑对冲):")
            print("-" * 70)
            
            for rec in optional_hedges:
                if rec.hedge_side != 'none' and abs(rec.current_delta) > 0.001:
                    print(f"{rec.underlying:<6} {rec.current_delta:>+10.4f} {rec.hedge_side.upper():<8} "
                          f"{rec.required_hedge_amount:<10.4f} ${rec.current_price:<9.2f} ${rec.hedge_value:<9.2f}")
        
        if not required_hedges:
            print("\n✅ 当前Delta敞口在可接受范围内，无需强制对冲")
            return False
        
        # 询问用户确认
        print(f"\n⚠️  检测到超过阈值({self.hedge_threshold*100:.1f}%)的Delta敞口")
        print("是否执行自动对冲？这将在Lighter平台下市价单")
        
        while True:
            try:
                confirm = input("\n请确认 [yes/no/details]: ").strip().lower()
                
                if confirm in ['yes', 'y', '是', '确认']:
                    return True
                elif confirm in ['no', 'n', '否', '取消']:
                    return False
                elif confirm in ['details', 'd', '详情']:
                    self._show_detailed_analysis(required_hedges)
                else:
                    print("请输入 yes/no/details")
            except (KeyboardInterrupt, EOFError):
                print("\n❌ 对冲已取消")
                return False
    
    def _show_detailed_analysis(self, recommendations: List[HedgeRecommendation]):
        """显示详细分析"""
        print("\n" + "=" * 60)
        print("📊 详细对冲分析")
        print("=" * 60)
        
        for rec in recommendations:
            if rec.hedge_side == 'none':
                continue
                
            print(f"\n🎯 {rec.underlying}:")
            print(f"   当前Delta敞口: {rec.current_delta:+.6f}")
            print(f"   建议对冲方向: {rec.hedge_side.upper()}")
            print(f"   建议对冲数量: {rec.required_hedge_amount:.4f} {rec.underlying}")
            print(f"   当前价格: ${rec.current_price:.2f}")
            print(f"   对冲预估成本: ${rec.hedge_value:.2f}")
            
            # 获取精度信息
            try:
                size_decimals = self.lighter_api.get_size_decimals(rec.underlying)
                price_decimals = self.lighter_api.get_price_decimals(rec.underlying)
                
                # 根据精度格式化数量
                formatted_amount = round(rec.required_hedge_amount, size_decimals)
                formatted_price = round(rec.current_price, price_decimals)
                
                print(f"   实际下单数量: {formatted_amount:.{size_decimals}f} {rec.underlying}")
                print(f"   实际下单价格: ${formatted_price:.{price_decimals}f}")
                
            except Exception as e:
                print(f"   ⚠️  获取交易精度失败: {e}")
    
    async def execute_hedge_orders(self, recommendations: List[HedgeRecommendation]) -> List[HedgeResult]:
        """
        执行对冲订单
        
        Args:
            recommendations: 对冲建议列表
            
        Returns:
            List[HedgeResult]: 执行结果列表
        """
        results = []
        required_hedges = [r for r in recommendations if r.is_required and r.hedge_side != 'none']
        
        if not required_hedges:
            print("✅ 无需执行对冲订单")
            return results
        
        print(f"\n🚀 开始执行{len(required_hedges)}个对冲订单...")
        
        for i, rec in enumerate(required_hedges, 1):
            print(f"\n[{i}/{len(required_hedges)}] 执行 {rec.underlying} 对冲...")
            
            try:
                # 获取交易精度
                size_decimals = self.lighter_api.get_size_decimals(rec.underlying)
                if size_decimals is None:
                    raise Exception(f"无法获取{rec.underlying}的交易精度")
                
                # 根据精度格式化数量
                formatted_amount = round(rec.required_hedge_amount, size_decimals)
                
                if formatted_amount == 0:
                    print(f"⚠️  对冲数量过小，跳过 {rec.underlying}")
                    continue
                
                # 计算价格（市价单使用当前价格的±5%作为最差价格）
                if rec.hedge_side == 'buy':
                    worst_price = rec.current_price * 1.05  # 买入时价格上限
                else:
                    worst_price = rec.current_price * 0.95  # 卖出时价格下限
                
                print(f"   {rec.hedge_side.upper()} {formatted_amount:.{size_decimals}f} {rec.underlying}")
                print(f"   最差价格: ${worst_price:.4f}")
                
                # 下市价单
                is_ask = rec.hedge_side == 'sell'
                tx_hash = await self.lighter_trader.create_market_order(
                    symbol=rec.underlying,
                    amount=formatted_amount,
                    price=worst_price,
                    is_ask=is_ask
                )
                
                if tx_hash:
                    
                    print(f"   ✅ 订单提交成功: {tx_hash[:16]}...")
                    
                    # 记录到数据库
                    self.db.add_hedge_order(
                        platform="lighter",
                        symbol=rec.underlying,
                        side=rec.hedge_side,
                        quantity=formatted_amount,
                        price=rec.current_price,
                        order_hash=' '.join(tx_hash)
                    )
                    
                    results.append(HedgeResult(
                        success=True,
                        underlying=rec.underlying,
                        side=rec.hedge_side,
                        amount=formatted_amount,
                        price=rec.current_price,
                        tx_hash=' '.join(tx_hash)
                    ))
                else:
                    print(f"   ❌ 订单提交失败")
                    results.append(HedgeResult(
                        success=False,
                        underlying=rec.underlying,
                        side=rec.hedge_side,
                        amount=formatted_amount,
                        price=rec.current_price,
                        error_message="订单提交失败"
                    ))
                
                # 延迟避免API限制
                if i < len(required_hedges):
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"   ❌ 执行失败: {e}")
                results.append(HedgeResult(
                    success=False,
                    underlying=rec.underlying,
                    side=rec.hedge_side if rec.hedge_side != 'none' else 'unknown',
                    amount=rec.required_hedge_amount,
                    price=rec.current_price,
                    error_message=str(e)
                ))
        
        return results
    
    def display_hedge_results(self, results: List[HedgeResult]):
        """显示对冲执行结果"""
        if not results:
            return
        
        print(f"\n" + "=" * 70)
        print("📋 对冲执行结果")
        print("=" * 70)
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        if successful:
            print(f"\n✅ 成功执行的对冲订单 ({len(successful)}个):")
            print("-" * 70)
            print(f"{'标的':<6} {'方向':<6} {'数量':<12} {'价格':<10} {'交易哈希':<20}")
            print("-" * 70)
            
            total_value = 0
            for result in successful:
                value = result.amount * result.price
                total_value += value
                tx_short = result.tx_hash[:16] + "..." if result.tx_hash else "N/A"
                
                print(f"{result.underlying:<6} {result.side.upper():<6} {result.amount:<10.4f} "
                      f"${result.price:<9.2f} {tx_short:<20}")
            
            print("-" * 70)
            print(f"成功对冲总价值: ${total_value:.2f}")
        
        if failed:
            print(f"\n❌ 失败的对冲订单 ({len(failed)}个):")
            print("-" * 50)
            
            for result in failed:
                print(f"   {result.underlying} {result.side.upper()} {result.amount:.4f}")
                print(f"   错误: {result.error_message}")
    
    def update_position_cache(self, positions: List, delta_summary: Dict[str, float]):
        """更新仓位缓存"""
        self.last_positions = positions.copy() if positions else {}
        self.last_delta_summary = delta_summary.copy()
    
    async def run_hedge_cycle(self, current_positions, current_delta_summary: Dict[str, float]) -> bool:
        """
        运行一个完整的对冲周期
        
        Args:
            current_positions: 当前期权仓位
            current_delta_summary: 当前Delta汇总
            
        Returns:
            bool: 是否执行了对冲
        """
        print(f"\n🔍 检查对冲需求...")
        print(f"对冲阈值: {self.hedge_threshold*100:.1f}%")
        
        # 1. 分析对冲需求
        recommendations = self.check_hedge_requirement(current_delta_summary)
        
        # 2. 显示建议并询问确认
        should_hedge = self.display_hedge_recommendations(recommendations)
        
        if not should_hedge:
            print("❌ 用户取消对冲操作")
            return False
        
        # 3. 执行对冲订单
        try:
            results = await self.execute_hedge_orders(recommendations)
            
            # 4. 显示执行结果
            self.display_hedge_results(results)
            
            # 5. 更新缓存
            self.update_position_cache(current_positions, current_delta_summary)
            
            # 检查是否有成功的订单
            successful_orders = [r for r in results if r.success]
            
            if successful_orders:
                print(f"\n✅ 对冲执行完成，成功下单 {len(successful_orders)} 个")
                return True
            else:
                print(f"\n❌ 对冲执行失败，所有订单都未成功")
                return False
                
        except Exception as e:
            print(f"❌ 执行对冲时出错: {e}")
            return False
        finally:
            # 断开交易连接
            await self.lighter_trader.disconnect()


def test_hedge_engine():
    """测试对冲引擎"""
    async def test_async():
        hedge_engine = HedgeEngine(hedge_threshold=0.05)
        
        # 模拟Delta数据
        test_delta_summary = {
            'SOL': 0.15,   # 需要对冲
            'BTC': -0.05,  # 边界情况
            'ETH': 0.02,   # 不需要对冲
        }
        
        # 更新缓存（模拟之前的状态）
        hedge_engine.last_delta_summary = {
            'SOL': 0.0,
            'BTC': 0.0, 
            'ETH': 0.0,
        }
        
        print("测试对冲引擎...")
        
        # 检查对冲需求
        recommendations = hedge_engine.check_hedge_requirement(test_delta_summary)
        
        print(f"\n获得 {len(recommendations)} 个对冲建议:")
        for rec in recommendations:
            print(f"  {rec.underlying}: Delta={rec.current_delta:+.4f}, "
                  f"需要{rec.hedge_side} {rec.required_hedge_amount:.4f}, "
                  f"必需={rec.is_required}")
        
        # 显示建议（但不实际执行）
        hedge_engine.display_hedge_recommendations(recommendations)
    
    asyncio.run(test_async())


if __name__ == "__main__":
    test_hedge_engine()