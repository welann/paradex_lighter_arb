#!/usr/bin/env python3
"""
期权对冲系统
用于自动对冲Paradex期权仓位的delta风险
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from option_positions_db import OptionPositionsDB
from lighter_market import LighterMarketAPI
from lighter_account import get_position_by_symbol
from lighter_trading import LighterTrader
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('urllib3').setLevel(logging.ERROR)

load_dotenv()

@dataclass
class HedgeRequirement:
    """对冲需求数据类"""
    underlying_symbol: str
    current_delta: float
    current_price: float
    required_hedge_amount: float
    current_position: float
    position_diff: float
    threshold_met: bool
    action_needed: str  # "BUY", "SELL", "NONE"

class HedgeSystem:
    """期权对冲系统"""
    
    def __init__(self, threshold_pct: float = 5.0):
        """
        初始化对冲系统
        
        Args:
            threshold_pct: 对冲阈值百分比，默认5%
        """
        self.threshold_pct = threshold_pct
        self.db = OptionPositionsDB()
        self.lighter_market = LighterMarketAPI()
        self.trader = LighterTrader()
        self.account_index = int(os.getenv('ACCOUNT_INDEX', 0))
        
        # 期权合约到标的资产的映射
        self.option_to_underlying = {
            "SOL": "SOL",
            "ETH": "ETH", 
            "BTC": "BTC",
            "HYPE": "HYPE"
        }
    
    def extract_underlying_symbol(self, option_symbol: str) -> Optional[str]:
        """
        从期权合约代码提取标的资产符号
        
        Args:
            option_symbol: 期权合约代码，如 "SOL-USD-215-C"
            
        Returns:
            Optional[str]: 标的资产符号，如 "SOL"
        """
        try:
            parts = option_symbol.split('-')
            if len(parts) >= 1:
                underlying = parts[0].upper()
                if underlying in self.option_to_underlying:
                    return self.option_to_underlying[underlying]
            
            logger.warning(f"无法识别期权合约的标的资产: {option_symbol}")
            return None
            
        except Exception as e:
            logger.error(f"提取标的资产符号失败: {option_symbol}, 错误: {e}")
            return None
    
    def calculate_delta_exposure_by_underlying(self) -> Dict[str, float]:
        """
        按标的资产计算总delta敞口
        
        Returns:
            Dict[str, float]: 标的资产到总delta的映射
        """
        positions = self.db.get_all_positions()
        delta_by_underlying = {}
        
        for position in positions:
            underlying = self.extract_underlying_symbol(position['symbol'])
            if underlying and position['delta'] is not None:
                total_position_delta = position['quantity'] * position['delta']
                
                if underlying in delta_by_underlying:
                    delta_by_underlying[underlying] += total_position_delta
                else:
                    delta_by_underlying[underlying] = total_position_delta
        
        return delta_by_underlying
    
    def get_hedge_requirements(self) -> List[HedgeRequirement]:
        """
        计算所有标的资产的对冲需求
        
        Returns:
            List[HedgeRequirement]: 对冲需求列表
        """
        hedge_requirements = []
        delta_exposures = self.calculate_delta_exposure_by_underlying()
        
        for underlying, total_delta in delta_exposures.items():
            try:
                # 获取当前价格
                market_data = self.lighter_market.get_market_by_symbol(underlying)
                if not market_data:
                    logger.error(f"无法获取{underlying}的市场数据")
                    continue
                
                current_price = market_data.last_trade_price
                if current_price <= 0:
                    logger.error(f"{underlying}价格无效: {current_price}")
                    continue
                
                # 计算需要对冲的数量 (delta * 价格 = 美元敞口)
                required_hedge_amount = abs(total_delta)
                
                # 获取当前在Lighter上的仓位
                current_position_data = get_position_by_symbol(self.account_index, underlying)
                current_position = 0.0
                if current_position_data:
                    current_position = abs(float(current_position_data.get('position', '0')))
                
                # 计算差距
                position_diff = abs(required_hedge_amount - current_position)
                threshold_amount = required_hedge_amount * (self.threshold_pct / 100.0)
                threshold_met = position_diff > threshold_amount
                
                # 确定操作方向
                action_needed = "NONE"
                if threshold_met:
                    if required_hedge_amount > current_position:
                        # 需要增加对冲仓位
                        if total_delta > 0:
                            action_needed = "SELL"  # delta为正，需要卖空对冲
                        else:
                            action_needed = "BUY"   # delta为负，需要买入对冲
                    else:
                        # 需要减少对冲仓位
                        if total_delta > 0:
                            action_needed = "BUY"   # 平空仓
                        else:
                            action_needed = "SELL"  # 平多仓
                
                hedge_req = HedgeRequirement(
                    underlying_symbol=underlying,
                    current_delta=total_delta,
                    current_price=current_price,
                    required_hedge_amount=required_hedge_amount,
                    current_position=current_position,
                    position_diff=position_diff,
                    threshold_met=threshold_met,
                    action_needed=action_needed
                )
                
                hedge_requirements.append(hedge_req)
                
            except Exception as e:
                logger.error(f"计算{underlying}对冲需求失败: {e}")
                continue
        
        return hedge_requirements
    
    async def execute_hedge_order(self, hedge_req: HedgeRequirement) -> Optional[str]:
        """
        执行对冲订单
        
        Args:
            hedge_req: 对冲需求
            
        Returns:
            Optional[str]: 交易哈希，失败返回None
        """
        if hedge_req.action_needed == "NONE":
            return None
        
        try:
            # 计算交易数量
            trade_amount = hedge_req.position_diff
            
            # 确定是买入还是卖出
            is_ask = hedge_req.action_needed == "SELL"
            
            # 设置价格容忍度（1%）
            price_tolerance = 0.01
            if is_ask:
                # 卖出时设置最低可接受价格
                order_price = hedge_req.current_price * (1 - price_tolerance)
            else:
                # 买入时设置最高可接受价格  
                order_price = hedge_req.current_price * (1 + price_tolerance)
            
            logger.info(f"准备执行对冲订单:")
            logger.info(f"  标的: {hedge_req.underlying_symbol}")
            logger.info(f"  操作: {hedge_req.action_needed}")
            logger.info(f"  数量: {trade_amount}")
            logger.info(f"  价格: {order_price}")
            logger.info(f"  当前delta: {hedge_req.current_delta}")
            
            # 执行交易
            tx_hash = await self.trader.create_market_order(
                symbol=hedge_req.underlying_symbol,
                amount=trade_amount,
                price=order_price,
                is_ask=is_ask
            )
            
            if tx_hash:
                # logger.info(f"对冲订单执行成功: {tx_hash}")
                logger.info(f"对冲订单执行成功 ")
            else:
                logger.error(f"对冲订单执行失败")
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"执行对冲订单失败: {e}")
            return None
    
    def display_hedge_status(self, hedge_requirements: List[HedgeRequirement]):
        """
        显示对冲状态
        
        Args:
            hedge_requirements: 对冲需求列表
        """
        print("=" * 80)
        print("期权对冲状态分析")
        print("=" * 80)
        
        if not hedge_requirements:
            print("当前没有需要对冲的仓位")
            return
        
        for req in hedge_requirements:
            print(f"\n标的资产: {req.underlying_symbol}")
            print(f"总Delta敞口: {req.current_delta:.4f}")
            print(f"当前价格: ${req.current_price:.2f}")
            print(f"需要对冲数量: {req.required_hedge_amount:.4f}")
            print(f"当前持仓数量: {req.current_position:.4f}")
            print(f"数量差距: {req.position_diff:.4f}")
            print(f"阈值: {self.threshold_pct}% (${req.required_hedge_amount * self.threshold_pct / 100:.2f})")
            print(f"是否需要调整: {'是' if req.threshold_met else '否'}")
            if req.threshold_met:
                print(f"建议操作: {req.action_needed}")
            print("-" * 40)
        
        needs_hedge = [req for req in hedge_requirements if req.threshold_met]
        print(f"\n总结: {len(needs_hedge)}/{len(hedge_requirements)} 个标的需要对冲调整")
        print("=" * 80)
    
    async def run_hedge_cycle(self, execute_trades: bool = False):
        """
        运行一次完整的对冲周期
        
        Args:
            execute_trades: 是否实际执行交易，默认False（仅分析）
        """
        logger.info("开始对冲分析...")
        
        try:
            # 更新所有期权的delta值
            logger.info("更新期权delta值...")
            updated_count = self.db.update_all_deltas()
            logger.info(f"已更新{updated_count}个期权的delta值")
            
            # 计算对冲需求
            hedge_requirements = self.get_hedge_requirements()
            
            # 显示分析结果
            self.display_hedge_status(hedge_requirements)
            
            # 如果需要执行交易
            if execute_trades:
                needs_hedge = [req for req in hedge_requirements if req.threshold_met]
                
                if needs_hedge:
                    logger.info(f"准备执行{len(needs_hedge)}个对冲交易...")
                    
                    for req in needs_hedge:
                        logger.info(f"处理{req.underlying_symbol}的对冲...")
                        tx_hash = await self.execute_hedge_order(req)
                        
                        if tx_hash:
                            # print(f"✅ {req.underlying_symbol} 对冲完成: {tx_hash}")
                            print(f"✅ {req.underlying_symbol} 对冲完成 ")
                        else:
                            print(f"❌ {req.underlying_symbol} 对冲失败")
                        
                        # 等待一小段时间避免请求过于频繁
                        await asyncio.sleep(1)
                else:
                    logger.info("当前不需要执行任何对冲交易")
            else:
                logger.info("分析完成（未执行实际交易）")
                
        except Exception as e:
            logger.error(f"对冲周期执行失败: {e}")
        finally:
            await self.trader.disconnect()

async def main():
    """示例用法"""
    hedge_system = HedgeSystem(threshold_pct=5.0)
    
    # 仅分析，不执行交易
    print("=== 对冲分析模式 ===")
    await hedge_system.run_hedge_cycle(execute_trades=False)
    
    # 如果需要执行实际交易，取消下面的注释
    print("\n=== 对冲执行模式 ===") 
    await hedge_system.run_hedge_cycle(execute_trades=True)

if __name__ == "__main__":
    asyncio.run(main())