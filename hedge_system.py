#!/usr/bin/env python3
"""
期权对冲系统
用于自动对冲Paradex期权仓位的delta风险
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from option_positions_db import OptionPositionsDB
from lighter_market import LighterMarketAPI
from lighter_account import get_position_by_symbol
from lighter_trading import LighterTrader
import os
from datetime import datetime
from dotenv import load_dotenv
from logger_config import get_logger, get_current_log_file

# 获取日志记录器
logger = get_logger(__name__)
log_filename = get_current_log_file()

load_dotenv()

@dataclass
class HedgeRequirement:
    """对冲需求数据类"""
    underlying_symbol: str
    current_delta: float
    current_price: float
    target_hedge_position: float
    current_position: float
    position_diff: float
    trade_amount: float
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
        
        # 自动对冲控制标志
        self.auto_hedge_enabled = False
        self.hedge_interval = 10  # 对冲检查间隔（秒）
        
        # 记录日志文件位置
        logger.info(f"对冲系统初始化完成，日志文件: {log_filename}")
    
    def get_log_filename(self) -> str:
        """获取当前日志文件名"""
        return log_filename
    
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
                
                # 计算目标对冲仓位：delta为正需要short，delta为负需要long
                target_hedge_position = -total_delta
                
                # 获取当前在Lighter上的仓位（正数=long，负数=short）
                current_position_data = get_position_by_symbol(self.account_index, underlying)
                current_position = 0.0
                if current_position_data:
                    current_position = float(current_position_data.get('position', '0'))
                
                # 计算需要调整的仓位差额
                position_diff = target_hedge_position - current_position
                
                # 计算阈值（基于目标仓位的绝对值）
                threshold_amount = abs(target_hedge_position) * (self.threshold_pct / 100.0)
                threshold_met = abs(position_diff) > threshold_amount
                
                # 确定操作方向和数量
                action_needed = "NONE"
                trade_amount = 0.0
                
                if threshold_met:
                    trade_amount = abs(position_diff)
                    if position_diff > 0:
                        action_needed = "BUY"   # 需要买入（增加long或减少short）
                    else:
                        action_needed = "SELL"  # 需要卖出（增加short或减少long）
                
                hedge_req = HedgeRequirement(
                    underlying_symbol=underlying,
                    current_delta=total_delta,
                    current_price=current_price,
                    target_hedge_position=target_hedge_position,
                    current_position=current_position,
                    position_diff=position_diff,
                    trade_amount=trade_amount,
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
            # 使用计算好的交易数量
            trade_amount = hedge_req.trade_amount
            
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
            print(f"目标对冲仓位: {req.target_hedge_position:.4f}")
            print(f"当前持仓: {req.current_position:.4f}")
            print(f"仓位差距: {req.position_diff:.4f}")
            print(f"阈值: {self.threshold_pct}% ({abs(req.target_hedge_position) * self.threshold_pct / 100:.4f})")
            print(f"是否需要调整: {'是' if req.threshold_met else '否'}")
            if req.threshold_met:
                print(f"建议操作: {req.action_needed} {req.trade_amount:.4f}")
            print("-" * 40)
        
        needs_hedge = [req for req in hedge_requirements if req.threshold_met]
        print(f"\n总结: {len(needs_hedge)}/{len(hedge_requirements)} 个标的需要对冲调整")
        print("=" * 80)
    
    async def run_hedge_cycle(self, execute_trades: bool = False, continuous: bool = False):
        """
        运行对冲周期
        
        Args:
            execute_trades: 是否实际执行交易，默认False（仅分析）
            continuous: 是否持续运行，默认False（单次执行）
        """
        logger.info(f"启动对冲周期 - {'持续模式' if continuous else '单次模式'} - ")
        if continuous:
            # 持续运行模式
            logger.info(f"{'='*50}")
            logger.info(f"启动持续对冲模式 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"执行模式: {'实际交易' if execute_trades else '仅分析'}")
            logger.info(f"对冲阈值: {self.threshold_pct}%")
            logger.info(f"检查间隔: {self.hedge_interval}秒")
            self.auto_hedge_enabled = True
            
            cycle_count = 0
            while self.auto_hedge_enabled:
                cycle_count += 1
                try:
                    logger.info(f"开始第 {cycle_count} 次对冲检查...")
                    await self._execute_single_hedge_cycle(execute_trades)
                    
                    logger.info(f"等待 {self.hedge_interval} 秒后进行下次检查...")
                    await asyncio.sleep(self.hedge_interval)
                        
                except Exception as e:
                    logger.error(f"第 {cycle_count} 次对冲检查失败: {e}", exc_info=True)
                    print(f"❌ 对冲检查出错: {e}")
                    logger.info("等待30秒后重试...")
                    await asyncio.sleep(30)
            
            logger.info(f"持续对冲模式已停止 - 共执行了 {cycle_count} 次检查")
            logger.info(f"{'='*50}")
        else:
            # 单次执行模式
            logger.info(f"启动对冲周期 - '单次模式' ")
            await self._execute_single_hedge_cycle(execute_trades)
    
    async def _execute_single_hedge_cycle(self, execute_trades: bool = False):
        """执行单次对冲周期"""
        cycle_start_time = datetime.now()
        logger.info(f"{'='*50}")
        logger.info(f"开始对冲周期分析 - {cycle_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"执行模式: {'实际交易' if execute_trades else '仅分析'}")
        logger.info(f"对冲阈值: {self.threshold_pct}%")
        
        try:
            # 更新所有期权的delta值
            updated_count = self.db.update_all_deltas()
            logger.info(f"步骤1: 成功更新 {updated_count} 个期权的delta值")
            
            # 计算对冲需求
            hedge_requirements = self.get_hedge_requirements()
            logger.info(f"步骤2: 计算对冲需求，发现 {len(hedge_requirements)} 个标的资产")
            
            # 记录详细的对冲需求信息
            for req in hedge_requirements:
                logger.info(f"标的 {req.underlying_symbol}: Delta={req.current_delta:.4f}, "
                           f"当前价格=${req.current_price:.2f}, "
                           f"目标仓位={req.target_hedge_position:.4f}, "
                           f"当前持仓={req.current_position:.4f}, "
                           f"差距={req.position_diff:.4f}, "
                           f"交易量={req.trade_amount:.4f}, "
                           f"超过阈值={'是' if req.threshold_met else '否'}")
            
            # 显示分析结果
            self.display_hedge_status(hedge_requirements)
            
            # 如果需要执行交易
            if execute_trades:
                needs_hedge = [req for req in hedge_requirements if req.threshold_met]
                
                if needs_hedge:
                    logger.info(f"步骤3: 执行对冲交易，共需处理 {len(needs_hedge)} 个标的...")
                    
                    success_count = 0
                    for i, req in enumerate(needs_hedge, 1):
                        logger.info(f"处理 {i}/{len(needs_hedge)}: {req.underlying_symbol} "
                                   f"({req.action_needed} {req.trade_amount:.4f})")
                        
                        tx_hash = await self.execute_hedge_order(req)
                        
                        if tx_hash:
                            logger.info(f"✅ {req.underlying_symbol} 对冲交易成功")
                            print(f"✅ {req.underlying_symbol} 对冲完成")
                            success_count += 1
                        else:
                            logger.error(f"❌ {req.underlying_symbol} 对冲交易失败")
                            print(f"❌ {req.underlying_symbol} 对冲失败")
                        
                        # 等待一小段时间避免请求过于频繁
                        await asyncio.sleep(1)
                    
                    logger.info(f"对冲交易完成: 成功 {success_count}/{len(needs_hedge)} 个")
                else:
                    logger.info("步骤3: 当前所有标的都在阈值范围内，无需执行对冲交易")
            else:
                needs_hedge_count = len([req for req in hedge_requirements if req.threshold_met])
                logger.info(f"分析完成: {needs_hedge_count} 个标的需要对冲（未执行实际交易）")
            
            # 记录周期完成信息
            cycle_end_time = datetime.now()
            duration = (cycle_end_time - cycle_start_time).total_seconds()
            logger.info(f"对冲周期完成 - 耗时 {duration:.2f} 秒")
            logger.info(f"{'='*50}")
                
        except Exception as e:
            logger.error(f"对冲周期执行失败: {e}", exc_info=True)
            print(f"❌ 对冲系统错误: {e}")
        finally:
            try:
                await self.trader.disconnect()
                logger.debug("交易客户端连接已断开")
            except Exception as e:
                logger.warning(f"断开交易客户端时出错: {e}")
    
    def stop_auto_hedge(self):
        """停止自动对冲"""
        self.auto_hedge_enabled = False
        logger.info("接收到停止自动对冲信号")
        
    def start_auto_hedge(self):
        """启动自动对冲"""
        self.auto_hedge_enabled = True
        logger.info("自动对冲已启用")
            
            
    def set_hedge_interval(self, interval: int=10):
        """设置对冲检查间隔"""
        if interval > 0:
            self.hedge_interval = interval
            logger.info(f"对冲检查间隔已设置为 {interval} 秒")
        else:
            logger.warning(f"无效的间隔时间: {interval}")
    
    def is_auto_hedge_enabled(self) -> bool:
        """检查自动对冲是否启用"""
        return self.auto_hedge_enabled

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