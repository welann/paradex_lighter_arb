#!/usr/bin/env python3
"""
快速测试SOL-USD-215-C的delta值
"""

from paradex_market import ParadexAPI

def main():
    api = ParadexAPI()
    
    symbol = "SOL-USD-215-C"
    delta = api.get_option_delta(symbol)
    
    print(f"期权合约: {symbol}")
    print(f"Delta值: {delta}")
    
    # 获取更详细的信息
    market = api.get_market_by_symbol(symbol)
    if market:
        print(f"标记价格: {market.mark_price}")
        print(f"隐含波动率: {market.mark_iv}")
        print(f"Greeks: {market.greeks}")

if __name__ == "__main__":
    main()