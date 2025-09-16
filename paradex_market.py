import requests
import json
import csv
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

    def calculate_funding_cost_per_unit_capital(self, option_symbol: str) -> Optional[Dict]:
        """
        计算每单位资金对应的资金费率

        对于期权合约，计算每8小时需要支付的资金费与期权成本的比率
        例如：ETH-USD-4500-C期权，每份每8小时资金费 = 4500 * 0.16%，期权成本 = 120

        Args:
            option_symbol: 期权合约代码，如 "ETH-USD-4500-C"

        Returns:
            Optional[Dict]: 包含计算结果的字典
            {
                'symbol': 合约代码,
                'strike_price': 行权价,
                'option_cost': 期权成本,
                'funding_fee_8h': 每8小时资金费,
                'funding_cost_ratio': 资金费与期权成本的比率,
                'annualized_funding_cost': 年化资金成本率
            }
        """
        market = self.get_market_by_symbol(option_symbol)
        if not market or not market.is_option:
            print(f"合约 {option_symbol} 不存在或不是期权合约")
            return None

        # 从期权代码中提取行权价
        try:
            # 期权格式例如: ETH-USD-4500-C
            parts = option_symbol.split('-')
            if len(parts) < 4:
                print(f"无效的期权合约格式: {option_symbol}")
                return None

            strike_price = float(parts[2])
        except (ValueError, IndexError):
            print(f"无法从合约代码中提取行权价: {option_symbol}")
            return None

        # 获取期权的mark价格作为期权成本
        option_cost = market.mark_price
        if option_cost is None:
            print(f"无法获取期权 {option_symbol} 的mark价格")
            return None

        # 获取资金费率 (假设为年化利率，需要转换为8小时费率)
        # 如果没有funding_rate，使用默认的0.16%
        funding_rate_annual = market.funding_rate if market.funding_rate is not None else 0
        funding_rate_annual=funding_rate_annual*8 
        # 计算每8小时的资金费
        funding_fee_8h = strike_price * funding_rate_annual

        # 计算资金费与期权成本的比率
        funding_cost_ratio = funding_fee_8h / option_cost


        result = {
            'symbol': option_symbol,
            'strike_price': strike_price,
            'option_cost': option_cost,
            'funding_fee_8h': funding_fee_8h,
            'funding_cost_ratio': funding_cost_ratio,
            'funding_rate_used': funding_rate_annual
        }

        return result


def main():
    api = ParadexAPI()

    # 获取所有期权合约
    option_markets = api.get_option_markets()
    print(f"找到 {len(option_markets)} 个期权合约")
    print("=" * 80)

    # 用于存储所有计算结果的列表
    results_data = []

    # 测试每个期权的资金费计算
    for option in option_markets:
        if option.mark_price is not None and option.mark_price > 0:
            result = api.calculate_funding_cost_per_unit_capital(option.symbol)

            if result:
                # 添加到结果列表
                results_data.append(result)

                # 控制台输出
                # print(f"期权: {result['symbol']}")
                # print(f"  行权价: ${result['strike_price']:.2f}")
                # print(f"  期权成本: ${result['option_cost']:.4f}")
                # print(f"  每8小时资金费: ${result['funding_fee_8h']:.6f}")
                # print(f"  资金费率: {result['funding_cost_ratio']:.6f} ({result['funding_cost_ratio']*100:.4f}%)")
                # print(f"  使用的资金费率: {result['funding_rate_used']:.6f}")
                # print("-" * 60)
            else:
                print(f"无法计算期权 {option.symbol} 的资金费")
        else:
            print(f"期权 {option.symbol} 没有有效的mark价格")

    # 将结果保存到CSV文件
    if results_data:
        csv_filename = 'option_funding_analysis.csv'

        # CSV文件的列标题
        fieldnames = [
            'symbol',
            'strike_price',
            'option_cost',
            'funding_fee_8h',
            'funding_cost_ratio',
            'funding_cost_percentage',
            'funding_rate_used'
        ]

        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # 写入标题行
            writer.writeheader()

            # 写入数据
            for result in results_data:
                writer.writerow({
                    'symbol': result['symbol'],
                    'strike_price': result['strike_price'],
                    'option_cost': result['option_cost'],
                    'funding_fee_8h': result['funding_fee_8h'],
                    'funding_cost_ratio': result['funding_cost_ratio'],
                    'funding_cost_percentage': result['funding_cost_ratio'] * 100,
                    'funding_rate_used': result['funding_rate_used']
                })

        print(f"\n数据已保存到 {csv_filename} 文件")
        print(f"共保存 {len(results_data)} 条期权数据")
    else:
        print("没有有效数据可以保存")

    print("\n" + "=" * 80)
    print("资金费计算完成")


if __name__ == "__main__":
    main()