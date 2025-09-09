from paradex_py import Paradex
import logging

# 初始化 Paradex 实例
paradex = Paradex()

# 获取全部市场
markets = paradex.api_client.fetch_markets()
for market in markets["results"]:
    if market.get("asset_kind") == "PERP_OPTION":
        symbol = market["symbol"]
        # 获取期权市场摘要信息，含隐含波动率等
        summary = paradex.api_client.fetch_markets_summary({"market": symbol})
        print(f"{symbol}: {summary}")

        # 获取订单簿（盘口）
        orderbook = paradex.api_client.fetch_orderbook(market=symbol)
        print(f"{symbol} Orderbook: {orderbook}")

        # 获取最优买卖价
        bbo = paradex.api_client.fetch_bbo(market=symbol)
        print(f"{symbol} BBO: {bbo}")
