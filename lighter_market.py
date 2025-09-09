#!/usr/bin/env python3
"""
Lighter市场信息处理模块
用于获取和解析Lighter DEX的市场数据
"""

import requests
import json
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class LighterMarketData:
    """Lighter市场数据类"""
    symbol: str
    market_id: int
    status: str
    taker_fee: float
    maker_fee: float
    liquidation_fee: float
    min_base_amount: str
    min_quote_amount: str
    supported_size_decimals: int
    supported_price_decimals: int
    supported_quote_decimals: int
    size_decimals: int
    price_decimals: int
    quote_multiplier: int
    default_initial_margin_fraction: int
    min_initial_margin_fraction: int
    maintenance_margin_fraction: int
    closeout_margin_fraction: int
    last_trade_price: float
    daily_trades_count: int
    daily_base_token_volume: int
    daily_quote_token_volume: float
    daily_price_low: float
    daily_price_high: float
    daily_price_change: float
    open_interest: int
    daily_chart: Dict = None


class LighterMarketAPI:
    """Lighter市场API客户端"""
    
    def __init__(self):
        self.base_url = "https://mainnet.zklighter.elliot.ai/api/v1"
        
        # 重点关注的市场映射
        self.target_markets = {
            0: "ETH",
            1: "BTC", 
            2: "SOL",
            24: "HYPE"
        }
    
    def get_market_details(self, market_id: int) -> Optional[LighterMarketData]:
        """
        获取指定市场的详细信息
        
        Args:
            market_id: 市场ID (0=ETH, 1=BTC, 2=SOL, 24=HYPE)
            
        Returns:
            Optional[LighterMarketData]: 市场数据，获取失败返回None
        """
        url = f"{self.base_url}/orderBookDetails"
        params = {"market_id": market_id}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == 200:
                order_book_details = data.get("order_book_details", [])
                if order_book_details:
                    return self._parse_market_data(order_book_details[0])
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"API请求错误 (market_id={market_id}): {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析错误 (market_id={market_id}): {e}")
            return None
    
    def get_all_target_markets(self) -> Dict[str, LighterMarketData]:
        """
        获取所有目标市场的数据
        
        Returns:
            Dict[str, LighterMarketData]: 市场名称到市场数据的映射
        """
        markets = {}
        
        for market_id, symbol in self.target_markets.items():
            market_data = self.get_market_details(market_id)
            if market_data:
                markets[symbol] = market_data
            else:
                print(f"警告: 无法获取 {symbol} (market_id={market_id}) 的市场数据")
        
        return markets
    
    def get_market_by_symbol(self, symbol: str) -> Optional[LighterMarketData]:
        """
        根据代币符号获取市场数据
        
        Args:
            symbol: 代币符号 ("ETH", "BTC", "SOL", "HYPE")
            
        Returns:
            Optional[LighterMarketData]: 市场数据
        """
        symbol = symbol.upper()
        
        # 找到对应的market_id
        market_id = None
        for mid, sym in self.target_markets.items():
            if sym == symbol:
                market_id = mid
                break
        
        if market_id is None:
            print(f"不支持的市场符号: {symbol}")
            return None
        
        return self.get_market_details(market_id)
    
    def get_size_decimals(self, symbol: str) -> Optional[int]:
        """
        获取指定币种的size_decimals
        
        Args:
            symbol: 代币符号 ("ETH", "BTC", "SOL", "HYPE")
            
        Returns:
            Optional[int]: size_decimals值，获取失败返回None
        """
        market_data = self.get_market_by_symbol(symbol)
        if market_data:
            return market_data.size_decimals
        return None
    
    def get_all_size_decimals(self) -> Dict[str, int]:
        """
        获取所有目标币种的size_decimals
        
        Returns:
            Dict[str, int]: 币种符号到size_decimals的映射
        """
        size_decimals_map = {}
        
        for symbol in self.target_markets.values():
            size_decimals = self.get_size_decimals(symbol)
            if size_decimals is not None:
                size_decimals_map[symbol] = size_decimals
        
        return size_decimals_map
    
    def get_price_decimals(self, symbol: str) -> Optional[int]:
        """
        获取指定币种的price_decimals
        
        Args:
            symbol: 代币符号 ("ETH", "BTC", "SOL", "HYPE")
            
        Returns:
            Optional[int]: price_decimals值，获取失败返回None
        """
        market_data = self.get_market_by_symbol(symbol)
        if market_data:
            return market_data.price_decimals
        return None
    
    def get_all_price_decimals(self) -> Dict[str, int]:
        """
        获取所有目标币种的price_decimals
        
        Returns:
            Dict[str, int]: 币种符号到price_decimals的映射
        """
        price_decimals_map = {}
        
        for symbol in self.target_markets.values():
            price_decimals = self.get_price_decimals(symbol)
            if price_decimals is not None:
                price_decimals_map[symbol] = price_decimals
        
        return price_decimals_map
    
    def _parse_market_data(self, data: Dict) -> LighterMarketData:
        """
        解析API返回的市场数据
        
        Args:
            data: API返回的原始数据
            
        Returns:
            LighterMarketData: 解析后的市场数据
        """
        return LighterMarketData(
            symbol=data.get("symbol", ""),
            market_id=data.get("market_id", 0),
            status=data.get("status", ""),
            taker_fee=self._safe_float(data.get("taker_fee")),
            maker_fee=self._safe_float(data.get("maker_fee")),
            liquidation_fee=self._safe_float(data.get("liquidation_fee")),
            min_base_amount=data.get("min_base_amount", ""),
            min_quote_amount=data.get("min_quote_amount", ""),
            supported_size_decimals=data.get("supported_size_decimals", 0),
            supported_price_decimals=data.get("supported_price_decimals", 0),
            supported_quote_decimals=data.get("supported_quote_decimals", 0),
            size_decimals=data.get("size_decimals", 0),
            price_decimals=data.get("price_decimals", 0),
            quote_multiplier=data.get("quote_multiplier", 0),
            default_initial_margin_fraction=data.get("default_initial_margin_fraction", 0),
            min_initial_margin_fraction=data.get("min_initial_margin_fraction", 0),
            maintenance_margin_fraction=data.get("maintenance_margin_fraction", 0),
            closeout_margin_fraction=data.get("closeout_margin_fraction", 0),
            last_trade_price=self._safe_float(data.get("last_trade_price")),
            daily_trades_count=data.get("daily_trades_count", 0),
            daily_base_token_volume=data.get("daily_base_token_volume", 0),
            daily_quote_token_volume=self._safe_float(data.get("daily_quote_token_volume")),
            daily_price_low=self._safe_float(data.get("daily_price_low")),
            daily_price_high=self._safe_float(data.get("daily_price_high")),
            daily_price_change=self._safe_float(data.get("daily_price_change")),
            open_interest=data.get("open_interest", 0),
            daily_chart=data.get("daily_chart", {})
        )
    
    def _safe_float(self, value) -> float:
        """
        安全转换为浮点数
        
        Args:
            value: 待转换的值
            
        Returns:
            float: 转换后的浮点数，失败返回0.0
        """
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


def main():
    """
    主测试函数
    """
    api = LighterMarketAPI()
    
    print("=" * 60)
    print("Lighter市场信息获取测试")
    print("=" * 60)
    
    # 获取所有目标市场数据
    markets = api.get_all_target_markets()
    
    print(f"\n成功获取 {len(markets)} 个市场的数据:")
    print("-" * 40)
    
    for symbol, market_data in markets.items():
        print(f"\n{symbol} (Market ID: {market_data.market_id})")
        print(f"  状态: {market_data.status}")
        print(f"  最新价格: ${market_data.last_trade_price}")
        print(f"  日交易量: {market_data.daily_base_token_volume:,} 代币")
        print(f"  日交易额: ${market_data.daily_quote_token_volume:,.2f}")
        print(f"  日涨跌幅: {market_data.daily_price_change:.2f}%")
        print(f"  未平仓合约: {market_data.open_interest:,}")
        print(f"  Maker费率: {market_data.maker_fee}%")
        print(f"  Taker费率: {market_data.taker_fee}%")
    
    print("\n" + "=" * 60)
    print("单独测试SOL市场")
    print("=" * 60)
    
    sol_market = api.get_market_by_symbol("SOL")
    if sol_market:
        print(f"SOL市场详情:")
        print(f"  市场ID: {sol_market.market_id}")
        print(f"  当前价格: ${sol_market.last_trade_price}")
        print(f"  24小时最高: ${sol_market.daily_price_high}")
        print(f"  24小时最低: ${sol_market.daily_price_low}")
        print(f"  24小时涨跌: {sol_market.daily_price_change:.2f}%")

    print("=" * 60)
    sol_decimals = api.get_size_decimals("SOL")
    print(f"SOL的size_decimals: {sol_decimals}")  # 输出: 3

if __name__ == "__main__":
    main()