import requests
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MarketData:
    symbol: str
    mark_price: Optional[float] = None
    last_traded_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume_24h: Optional[float] = None
    total_volume: Optional[float] = None
    underlying_price: Optional[float] = None
    open_interest: Optional[float] = None
    funding_rate: Optional[float] = None
    price_change_rate_24h: Optional[float] = None
    delta: Optional[float] = None
    greeks: Optional[Dict] = None
    created_at: Optional[int] = None
    
    # Option-specific fields
    mark_iv: Optional[float] = None
    bid_iv: Optional[float] = None
    ask_iv: Optional[float] = None
    last_iv: Optional[float] = None
    future_funding_rate: Optional[float] = None
    
    @property
    def is_perpetual(self) -> bool:
        """Check if this is a perpetual contract"""
        return "PERP" in self.symbol
    
    @property
    def is_option(self) -> bool:
        """Check if this is an options contract"""
        return ("-C" in self.symbol or "-P" in self.symbol) and not self.is_perpetual
    
    @property
    def contract_type(self) -> str:
        """Get contract type"""
        if self.is_perpetual:
            return "PERPETUAL"
        elif self.is_option:
            return "OPTION"
        else:
            return "UNKNOWN"


class ParadexAPI:
    def __init__(self):
        self.base_url = "https://api.prod.paradex.trade/v1"
    
    def get_markets_summary(self, market: str = "ALL") -> List[MarketData]:
 
        url = f"{self.base_url}/markets/summary"
        params = {"market": market}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            # API returns data in format {"results": [...]}
            results = data.get("results", [])
            return self._parse_market_data(results)
            
        except requests.exceptions.RequestException as e:
            print(f"API error: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")
            return []
    
    def _parse_market_data(self, data: List[Dict]) -> List[MarketData]:
 
        market_list = []
        
        for item in data:
            try:
                market = MarketData(
                    symbol=item.get("symbol", ""),
                    mark_price=self._safe_float(item.get("mark_price")),
                    last_traded_price=self._safe_float(item.get("last_traded_price")),
                    bid=self._safe_float(item.get("bid")),
                    ask=self._safe_float(item.get("ask")),
                    volume_24h=self._safe_float(item.get("volume_24h")),
                    total_volume=self._safe_float(item.get("total_volume")),
                    underlying_price=self._safe_float(item.get("underlying_price")),
                    open_interest=self._safe_float(item.get("open_interest")),
                    funding_rate=self._safe_float(item.get("funding_rate")),
                    price_change_rate_24h=self._safe_float(item.get("price_change_rate_24h")),
                    delta=self._safe_float(item.get("delta")),
                    greeks=item.get("greeks"),
                    created_at=self._safe_int(item.get("created_at")),
                    # Option-specific fields
                    mark_iv=self._safe_float(item.get("mark_iv")),
                    bid_iv=self._safe_float(item.get("bid_iv")),
                    ask_iv=self._safe_float(item.get("ask_iv")),
                    last_iv=self._safe_float(item.get("last_iv")),
                    future_funding_rate=self._safe_float(item.get("future_funding_rate"))
                )
                market_list.append(market)
                
            except Exception as e:
                print(f"item error: {item.get('symbol', 'Unknown')}: {e}")
                continue
        
        return market_list
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to integer"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def get_market_by_symbol(self, symbol: str) -> Optional[MarketData]:
 
        markets = self.get_markets_summary()
        for market in markets:
            if market.symbol == symbol:
                return market
        return None
    
    def filter_markets_by_type(self, market_type: str = "PERP") -> List[MarketData]:
 
        markets = self.get_markets_summary()
        return [market for market in markets if market_type in market.symbol]
    
    def get_perpetual_markets(self) -> List[MarketData]:
 
        markets = self.get_markets_summary()
        return [market for market in markets if market.is_perpetual]
    
    def get_option_markets(self) -> List[MarketData]:
 
        markets = self.get_markets_summary()
        return [market for market in markets if market.is_option]
    
    def get_markets_by_underlying(self, underlying: str) -> List[MarketData]:
        """
        根据标的资产获取市场数据
        
        Args:
            underlying: 标的资产名称，如 "BTC", "ETH"
            
        Returns:
            List[MarketData]: 该标的相关的所有合约
        """
        markets = self.get_markets_summary()
        return [market for market in markets if underlying in market.symbol]
    
    def get_option_delta(self, symbol: str) -> Optional[float]:
        """
        获取指定期权合约的delta值
        
        Args:
            symbol: 期权合约代码，如 "SOL-USD-215-C"
            
        Returns:
            Optional[float]: 期权的delta值，如果合约不存在或不是期权则返回None
        """
        market = self.get_market_by_symbol(symbol)
        if market and market.is_option:
            return market.delta
        return None


def main():
 
    api = ParadexAPI()
    
    markets = api.get_markets_summary()
    print(f"total {len(markets)} markets open")
    
 
    for market in markets[:5]:
        print(f"Symbol: {market.symbol}")
        print(f"Mark Price: {market.mark_price}")
        print(f"24h Volume: {market.volume_24h}")
        print(f"24h Change: {market.price_change_rate_24h}%")
        print("-" * 40)
 
    print("sol-115-C")
    sol_115_c=api.get_market_by_symbol("SOL-USD-215-C")
    print(sol_115_c)


if __name__ == "__main__":
    main()