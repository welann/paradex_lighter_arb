# 原理

这是一个使用lighter零手续费机制，对冲paradex上期权以便于获得资金费收入的程序

目前只考虑对冲期权的delta值，可以设置不同的阈值以便于调整对冲频率

需要先手动在paradex上下单
lighter当前需要邀请码

## 使用方式

+ 将 `.env.example` 文件名修改为 `.env`， 填写对应的api信息
+ 运行 `pip install uv`
+ 运行 `uv run main.py`

## paradex_info.py

https://api.prod.paradex.trade/v1/markets/summary?market=ALL

## lighter_order.py

在lighter上进行对冲