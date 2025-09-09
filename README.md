# 原理

这是一个使用lighter零手续费机制，对冲paradex上期权以便于获得资金费收入的程序

目前只考虑对冲期权的delta值，可以设置不同的阈值以便于调整对冲频率

需要先手动在paradex上下单
lighter当前需要邀请码

## 使用方式


## paradex_info.py

获取paradex上账号的持仓以及对应的希腊字母
https://api.prod.paradex.trade/v1/markets
更关注下面的信息
https://api.prod.paradex.trade/v1/markets/summary?market=ALL

先通过api获取各个合约的delta
然后手动指定每个合约仓位大小进行对冲

需要有：
一个命令行界面：展示对冲信息
能随时接受命令，比如 ：
add sell sol-120-c 2（卖出2张sol的120put，需要进行对冲）
delete sol-120-c 2(对原本的仓位进行平仓，可以不需要对冲了)


## lighter_order.py

在lighter上进行对冲