import os
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

def get_lighter_positions() -> Optional[List[Dict]]:
    """
    获取Lighter平台指定账户的仓位信息
    返回所有position_value > 0的仓位列表
    """
    load_dotenv()
    
    account_index = os.getenv('ACCOUNT_INDEX')
    if not account_index:
        print("错误：无法从.env文件读取ACCOUNT_INDEX")
        return None
    
    api_url = f"https://mainnet.zklighter.elliot.ai/api/v1/account?by=index&value={account_index}"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') != 200:
            print(f"API请求失败，错误代码：{data.get('code')}")
            return None
        
        accounts = data.get('accounts', [])
        if not accounts:
            print("未找到账户信息")
            return None
        
        account = accounts[0]
        positions = account.get('positions', [])
        
        positive_positions = []
        for position in positions:
            position_value = float(position.get('position_value', '0'))
            if position_value > 0:
                positive_positions.append(position)
        
        return positive_positions
        
    except requests.RequestException as e:
        print(f"网络请求错误：{e}")
        return None
    except ValueError as e:
        print(f"JSON解析错误：{e}")
        return None

def get_position_by_symbol(account_index: int, symbol: str) -> Optional[Dict]:
    """
    通过指定的account index查询指定symbol的持仓
    
    Args:
        account_index: 账户索引
        symbol: 交易对符号，如 'ETH', 'SOL'
    
    Returns:
        指定symbol的持仓信息，如果未找到则返回None
    """
    api_url = f"https://mainnet.zklighter.elliot.ai/api/v1/account?by=index&value={account_index}"
    
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('code') != 200:
            print(f"API请求失败，错误代码：{data.get('code')}")
            return None
        
        accounts = data.get('accounts', [])
        if not accounts:
            print("未找到账户信息")
            return None
        
        account = accounts[0]
        positions = account.get('positions', [])
        
        for position in positions:
            if position.get('symbol') == symbol.upper():
                return position
        
        print(f"未找到交易对 {symbol} 的持仓信息")
        return None
        
    except requests.RequestException as e:
        print(f"网络请求错误：{e}")
        return None
    except ValueError as e:
        print(f"JSON解析错误：{e}")
        return None

def display_positions():
    """
    显示所有持仓信息
    """
    positions = get_lighter_positions()
    
    if not positions:
        print("没有找到持仓信息或持仓价值均为0")
        return
    
    print(f"找到 {len(positions)} 个持仓：")
    print("-" * 80)
    
    for position in positions:
        symbol = position.get('symbol', 'N/A')
        position_size = position.get('position', '0')
        position_value = position.get('position_value', '0')
        avg_entry_price = position.get('avg_entry_price', '0')
        unrealized_pnl = position.get('unrealized_pnl', '0')
        
        print(f"交易对: {symbol}")
        print(f"仓位大小: {position_size}")
        print(f"仓位价值: {position_value}")
        print(f"平均入场价: {avg_entry_price}")
        print(f"未实现盈亏: {unrealized_pnl}")
        print("-" * 40)


def display_position_by_symbol(account_index: int, symbol: str):
    """
    显示指定symbol的持仓信息
    """
    position = get_position_by_symbol(account_index, symbol)
    
    if not position:
        print(f"未找到交易对 {symbol} 的持仓信息")
        return
    
    print(f"交易对: {position.get('symbol', 'N/A')}")
    print(f"仓位大小: {position.get('position', '0')}")
    print(f"仓位价值: {position.get('position_value', '0')}")
    print(f"平均入场价: {position.get('avg_entry_price', '0')}")
    print(f"未实现盈亏: {position.get('unrealized_pnl', '0')}")
    print("-" * 40)

if __name__ == "__main__":
    # display_positions()
    display_position_by_symbol(54, 'sui')