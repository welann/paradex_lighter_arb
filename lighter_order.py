import asyncio
import logging
import lighter
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

logging.basicConfig(level=logging.DEBUG)

# 从环境变量读取配置
BASE_URL = os.getenv("BASE_URL", "https://testnet.zklighter.elliot.ai")
API_KEY_PRIVATE_KEY = os.getenv("API_KEY_PRIVATE_KEY")
ACCOUNT_INDEX = int(os.getenv("ACCOUNT_INDEX"))
API_KEY_INDEX = int(os.getenv("API_KEY_INDEX"))

# 检查必需的环境变量
if not API_KEY_PRIVATE_KEY or not ACCOUNT_INDEX or not API_KEY_INDEX:
    raise ValueError("environment variable is required")


def trim_exception(e: Exception) -> str:
    return str(e).strip().split("\n")[-1]


async def main():
    client = lighter.SignerClient(
        url=BASE_URL,
        private_key=API_KEY_PRIVATE_KEY,
        account_index=ACCOUNT_INDEX,
        api_key_index=API_KEY_INDEX,
    )

    tx = await client.create_market_order(
        market_index=1,
        client_order_index=0,
        base_amount=100,  # 0.001 ETH
        avg_execution_price=170000,  # $1700 -- worst acceptable price for the order
        is_ask=True,
    )
    print("Create Order Tx:", tx)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())