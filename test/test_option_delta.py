#!/usr/bin/env python3
"""
测试获取期权delta值的功能
"""

from paradex_market import ParadexAPI

def test_option_delta():
    """测试期权delta获取功能"""
    api = ParadexAPI()
    
    print("=" * 60)
    print("期权Delta获取功能测试")
    print("=" * 60)
    
    # 测试用例列表
    test_symbols = [
        "SOL-USD-215-C",  # 用户要求的测试案例
        "BTC-USD-120000-C", # BTC看涨期权
        "ETH-USD-4000-P",   # ETH看跌期权
        "SOL-USD-PERP",     # 永续合约（应该返回None或delta值）
        "INVALID-SYMBOL"    # 无效合约
    ]
    
    print("\n测试期权Delta获取:")
    print("-" * 40)
    
    for symbol in test_symbols:
        delta = api.get_option_delta(symbol)
        
        # 获取完整的市场数据来显示更多信息
        market = api.get_market_by_symbol(symbol)
        
        print(f"\n合约: {symbol}")
        if market:
            print(f"  类型: {market.contract_type}")
            print(f"  是否期权: {market.is_option}")
            print(f"  Delta: {delta}")
            if market.is_option and market.greeks:
                print(f"  Greeks: {market.greeks}")
        else:
            print(f"  状态: 合约不存在")
            print(f"  Delta: {delta}")
    
    # 显示一些实际存在的SOL期权
    print("\n" + "=" * 60)
    print("实际存在的SOL期权示例")
    print("=" * 60)
    
    sol_markets = api.get_markets_by_underlying("SOL")
    sol_options = [m for m in sol_markets if m.is_option]
    
    print(f"找到 {len(sol_options)} 个SOL期权合约")
    
    # 显示前几个SOL期权的delta值
    for option in sol_options[:5]:
        delta = api.get_option_delta(option.symbol)
        print(f"  {option.symbol}: Delta = {delta}")

if __name__ == "__main__":
    test_option_delta()