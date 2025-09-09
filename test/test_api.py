#!/usr/bin/env python3
"""
测试Paradex API数据解析功能
"""

from paradex_market import ParadexAPI

def test_api():
    """测试API功能"""
    api = ParadexAPI()
    
    print("=" * 60)
    print("Paradex API 数据解析测试")
    print("=" * 60)
    
    # 获取所有市场数据
    markets = api.get_markets_summary()
    print(f"\n✓ 总共获得 {len(markets)} 个市场数据")
    
    # 测试永续合约
    perp_markets = api.get_perpetual_markets()
    print(f"✓ 永续合约数量: {len(perp_markets)}")
    
    # 测试期权合约
    option_markets = api.get_option_markets()
    print(f"✓ 期权合约数量: {len(option_markets)}")
    
    # 测试BTC相关市场
    btc_markets = api.get_markets_by_underlying("BTC")
    print(f"✓ BTC相关市场数量: {len(btc_markets)}")
    
    print("\n" + "=" * 60)
    print("永续合约示例 (BTC-USD-PERP)")
    print("=" * 60)
    
    btc_perp = api.get_market_by_symbol("BTC-USD-PERP")
    if btc_perp:
        print(f"合约类型: {btc_perp.contract_type}")
        print(f"是否为永续合约: {btc_perp.is_perpetual}")
        print(f"标记价格: {btc_perp.mark_price}")
        print(f"24小时涨跌幅: {btc_perp.price_change_rate_24h}%")
        print(f"资金费率: {btc_perp.funding_rate}")
        print(f"Delta: {btc_perp.delta}")
    
    print("\n" + "=" * 60)
    print("期权合约示例")
    print("=" * 60)
    
    if option_markets:
        option = option_markets[0]
        print(f"合约代码: {option.symbol}")
        print(f"合约类型: {option.contract_type}")
        print(f"是否为期权合约: {option.is_option}")
        print(f"标记价格: {option.mark_price}")
        print(f"标记隐含波动率: {option.mark_iv}")
        print(f"买价隐含波动率: {option.bid_iv}")
        print(f"卖价隐含波动率: {option.ask_iv}")
        print(f"Delta: {option.delta}")
        if option.greeks:
            print(f"Greeks数据: {option.greeks}")
    
    print("\n" + "=" * 60)
    print("数据统计汇总")
    print("=" * 60)
    
    print(f"总计: {len(markets)} 个合约")
    print(f"  - 永续合约: {len(perp_markets)} 个")
    print(f"  - 期权合约: {len(option_markets)} 个")
    print(f"  - 其他: {len(markets) - len(perp_markets) - len(option_markets)} 个")

if __name__ == "__main__":
    test_api()