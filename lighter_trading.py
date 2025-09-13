#!/usr/bin/env python3
"""
Lighter交易功能模块
封装下单和交易相关的功能
"""

import asyncio
import lighter
import os
from dotenv import load_dotenv
from typing import Optional
from lighter_market import LighterMarketAPI
from logger_config import get_logger

# 加载.env文件
load_dotenv()

# 获取日志记录器
logger = get_logger(__name__)

class LighterTrader:
    """Lighter交易客户端"""
    
    def __init__(self):
        # 从环境变量读取配置
        self.base_url = os.getenv("BASE_URL", "https://testnet.zklighter.elliot.ai")
        self.api_key_private_key = os.getenv("API_KEY_PRIVATE_KEY")
        self.account_index = int(os.getenv("ACCOUNT_INDEX"))
        self.api_key_index = int(os.getenv("API_KEY_INDEX"))
        
        # 检查必需的环境变量
        if not self.api_key_private_key:
            raise ValueError("API_KEY_PRIVATE_KEY environment variable is required")
        
        # 市场API客户端
        self.market_api = LighterMarketAPI()
        
        # 币种到market_index的映射
        self.symbol_to_market_id = {
            "ETH": 0,
            "BTC": 1,
            "SOL": 2,
            "HYPE": 24
        }
        
        self.client = None
    
    async def connect(self):
        """连接到Lighter客户端"""
        if self.client is None:
            self.client = lighter.SignerClient(
                url=self.base_url,
                private_key=self.api_key_private_key,
                account_index=self.account_index,
                api_key_index=self.api_key_index,
            )
            logger.info("已连接到Lighter客户端")
    
    async def disconnect(self):
        """断开客户端连接"""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("已断开Lighter客户端连接")
    
    async def create_market_order(
        self,
        symbol: str,
        amount: float,
        price: float,
        is_ask: bool = True,
        client_order_index: int = 0
    ) -> Optional[str]:
        """
        创建市价订单
        
        Args:
            symbol: 币种符号 ("ETH", "BTC", "SOL", "HYPE")
            amount: 交易数量
            price: 最差可接受价格 (对于买单是最高价，卖单是最低价)
            is_ask: True为卖出，False为买入
            client_order_index: 客户端订单索引
            
        Returns:
            Optional[str]: 交易哈希，失败返回None
        """
        try:
            # 连接客户端
            await self.connect()
            
            # 获取market_index
            market_index = self._get_market_index(symbol)
            if market_index is None:
                logger.error(f"不支持的币种: {symbol}")
                return None
            
            # 获取size_decimals进行数量格式化
            size_decimals = self.market_api.get_size_decimals(symbol)
            if size_decimals is None:
                logger.error(f"无法获取{symbol}的size_decimals")
                return None
            
            # 格式化交易数量
            formatted_amount = self._format_amount(amount, size_decimals)
            
            # 将价格转换为整数（通常需要乘以价格精度）
            price_decimals=self.market_api.get_price_decimals(symbol)
            if price_decimals is None:
                logger.error(f"无法获取{symbol}的price_decimals")
                return None
            
            # 根据买卖的不同方向，设定不同的滑点
            price= price*0.9 if is_ask else price*1.1
            
            formatted_price = self._format_price(price,price_decimals)  # 假设价格精度为2位小数
            
            logger.info(f"创建市价订单: {symbol} {formatted_amount} {size_decimals} @ ${formatted_price} {price_decimals}")
            logger.info(f"Market Index: {market_index}, Is Ask: {is_ask}")
            
            # 创建订单
            tx_result = await self.client.create_market_order(
                market_index=market_index,
                client_order_index=client_order_index,
                base_amount=formatted_amount,
                avg_execution_price=formatted_price,
                is_ask=is_ask,
            )

            # logger.info(f"订单创建成功: {tx}")
            logger.info(f"订单创建成功")
            return tx_result
            
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return None
    
    # async def create_limit_order(
    #     self,
    #     symbol: str,
    #     amount: float,
    #     price: float,
    #     is_ask: bool = True,
    #     client_order_index: int = 0
    # ) -> Optional[str]:
    #     """
    #     创建限价订单
        
    #     Args:
    #         symbol: 币种符号 ("ETH", "BTC", "SOL", "HYPE")
    #         amount: 交易数量
    #         price: 限价价格
    #         is_ask: True为卖出，False为买入
    #         client_order_index: 客户端订单索引
            
    #     Returns:
    #         Optional[str]: 交易哈希，失败返回None
    #     """
    #     try:
    #         # 连接客户端
    #         await self.connect()
            
    #         # 获取market_index
    #         market_index = self._get_market_index(symbol)
    #         if market_index is None:
    #             logger.error(f"不支持的币种: {symbol}")
    #             return None
            
    #         # 获取size_decimals进行数量格式化
    #         size_decimals = self.market_api.get_size_decimals(symbol)
    #         if size_decimals is None:
    #             logger.error(f"无法获取{symbol}的size_decimals")
    #             return None
            
    #         # 格式化交易数量
    #         formatted_amount = self._format_amount(amount, size_decimals)
            
    #         # 将价格转换为整数
    #         formatted_price = int(price * 100)
            
    #         logger.info(f"创建限价订单: {symbol} {formatted_amount} @ ${price}")
    #         logger.info(f"Market Index: {market_index}, Is Ask: {is_ask}")
            
    #         # 创建限价订单
    #         tx = await self.client.create_limit_order(
    #             market_index=market_index,
    #             client_order_index=client_order_index,
    #             base_amount=formatted_amount,
    #             price=formatted_price,
    #             is_ask=is_ask,
    #         )
            
    #         logger.info(f"限价订单创建成功: {tx}")
    #         return tx
            
    #     except Exception as e:
    #         logger.error(f"创建限价订单失败: {e}")
    #         return None
    
    def _get_market_index(self, symbol: str) -> Optional[int]:
        """
        获取币种对应的market_index
        
        Args:
            symbol: 币种符号
            
        Returns:
            Optional[int]: market_index
        """
        return self.symbol_to_market_id.get(symbol.upper())
    
    def _format_amount(self, amount: float, size_decimals: int) -> int:
        """
        根据size_decimals格式化交易数量
        
        Args:
            amount: 原始数量
            size_decimals: 小数位精度
            
        Returns:
            int: 格式化后的数量（整数）
        """
        multiplier = 10 ** size_decimals
        return int(amount * multiplier)
    
    def _format_price(self,price:float,price_decimals:int)->int:
        multiplier = 10 ** (price_decimals)
        return int(price * multiplier)
    
    async def get_market_price(self, symbol: str) -> Optional[float]:
        """
        获取市场当前价格
        
        Args:
            symbol: 币种符号
            
        Returns:
            Optional[float]: 当前价格
        """
        market_data = self.market_api.get_market_by_symbol(symbol)
        if market_data:
            return market_data.last_trade_price
        return None


# 便利函数
async def place_market_order(
    symbol: str,
    amount: float,
    price: float,
    is_ask: bool = True
) -> Optional[str]:
    """
    下市价单的便利函数
    
    Args:
        symbol: 币种符号
        amount: 交易数量
        price: 最差可接受价格
        is_ask: True为卖出，False为买入
        
    Returns:
        Optional[str]: 交易哈希
    """
    trader = LighterTrader()
    try:
        tx = await trader.create_market_order(symbol, amount, price, is_ask)
        return tx
    finally:
        await trader.disconnect()


# async def place_limit_order(
#     symbol: str,
#     amount: float,
#     price: float,
#     is_ask: bool = True
# ) -> Optional[str]:
#     """
#     下限价单的便利函数
    
#     Args:
#         symbol: 币种符号
#         amount: 交易数量
#         price: 限价价格
#         is_ask: True为卖出，False为买入
        
#     Returns:
#         Optional[str]: 交易哈希
#     """
#     trader = LighterTrader()
#     try:
#         tx = await trader.create_limit_order(symbol, amount, price, is_ask)
#         return tx
#     finally:
#         await trader.disconnect()


async def main():
    """
    示例用法
    """
    trader = LighterTrader()
    buy_or_sell = True  # buy=Fasle, sell=True
    symbol = "SOL"
    
    try:
        # 获取SOL当前价格
        current_price = float(await trader.get_market_price(symbol))
        print(f"{symbol}当前价格: ${current_price}")
        
        order_price=current_price * 0.8  if buy_or_sell else current_price * 1.2
        # 示例：买入0.1个SOL，最高价格220
        tx = await trader.create_market_order(
            symbol=symbol,
            amount=0.01,
            price=order_price,
            is_ask=buy_or_sell  # False为买入
        )
        print(f"买入订单: {tx}")
        
        print("注意: 实际下单代码已注释，请根据需要取消注释")
        
    finally:
        await trader.disconnect()


if __name__ == "__main__":
    asyncio.run(main())