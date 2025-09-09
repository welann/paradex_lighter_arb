#!/usr/bin/env python3
"""
测试获取不同币种size_decimals功能
"""

from lighter_market import LighterMarketAPI

def test_size_decimals():
    """测试size_decimals获取功能"""
    api = LighterMarketAPI()
    
    print("=" * 60)
    print("币种Size Decimals获取功能测试")
    print("=" * 60)
    
    # 测试单个币种的size_decimals获取
    test_symbols = ["ETH", "BTC", "SOL", "HYPE"]
    
    print("\n单个币种Size Decimals:")
    print("-" * 40)
    
    for symbol in test_symbols:
        size_decimals = api.get_size_decimals(symbol)
        print(f"{symbol}: {size_decimals}")
    
    print("\n" + "=" * 60)
    print("所有目标币种Size Decimals汇总")
    print("=" * 60)
    
    # 获取所有币种的size_decimals
    all_size_decimals = api.get_all_size_decimals()
    
    print("\n所有币种的Size Decimals:")
    print("-" * 30)
    for symbol, decimals in all_size_decimals.items():
        print(f"{symbol}: {decimals}")
    
    # 显示完整市场信息以便对比
    print("\n" + "=" * 60)
    print("完整市场信息对比")
    print("=" * 60)
    
    markets = api.get_all_target_markets()
    
    for symbol, market_data in markets.items():
        print(f"\n{symbol} (Market ID: {market_data.market_id})")
        print(f"  Size Decimals: {market_data.size_decimals}")
        print(f"  Price Decimals: {market_data.price_decimals}")
        print(f"  Supported Size Decimals: {market_data.supported_size_decimals}")
        print(f"  Supported Price Decimals: {market_data.supported_price_decimals}")
        print(f"  Min Base Amount: {market_data.min_base_amount}")
        print(f"  Last Trade Price: ${market_data.last_trade_price}")

if __name__ == "__main__":
    test_size_decimals()