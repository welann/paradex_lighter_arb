# 原理

这是一个使用lighter零手续费机制，对冲paradex上期权以便于获得资金费收入的程序

目前只考虑对冲期权的delta值，可以设置不同的阈值以便于调整对冲频率

需要先手动在paradex上下单，然后添加在数据库中，记得期权名字要写对
张数买是正的，卖是负的，只对冲你想对冲的仓位即可，没输入数据库的是不会被对冲的

还有，paradex和lighter有宕机风险（我在测试代码的时候就遇到了一次paradex宕机），注意安全

我的邀请码：
https://app.paradex.trade/r/welan

## 使用方式

### 必须步骤
+ 将 `.env.example` 文件名修改为 `.env`， 填写对应的api信息
+ 运行 `pip install uv`
+ 运行 `uv sync`

### 方式一，ssh窗口不可以关闭

+ 运行 `uv run main.py`

### 方式二，ssh窗口可以关闭

+ 下载`npm`: `sudo apt install npm`
+ 下载`pm2`: `npm install pm2 -g`
+ 使用`pm2启动程序`: `pm2 start "uv run python main.py" --name arb_bot`
+ `pm2 attach 0` 进入交互窗口，输入 `help`
+ 根据界面的提示使用功能
+ 想退出了就 `Ctrl+C`
<img width="1102" height="147" alt="image" src="https://github.com/user-attachments/assets/2627ed1e-e6fc-43f0-9d50-132f6d5d3149" />


> 注意，在开启autohedge on后，命令行界面会被日志信息占满，此时你输入命令仍然是可以识别的

> 如果不习惯的话，那就再开一个命令行界面专门用来修改仓位好了 

![alt text](./resource/image.png)


## 各文件用途

+ `main.py` 程序入口
+ `hedge_system.py` 对冲逻辑实现
+ `lighter_account.py` 获取lighter账户持仓信息
+ `lighter_market.py` 获取lighter当前市场的基本信息
+ `lighter_trading.py` 提供在lighter平台下单功能
+ `option_positions_db.py` 管理paradex平台当前期权仓位（需手动添加）
+ `paradex_market.py` 获取paradex平台信息（期权的delta之类的）
