#!/usr/bin/env python3
"""
命令解析器模块
解析用户输入的命令并执行相应操作
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Command:
    """命令数据类"""
    action: str  # 'add', 'delete', 'show', 'help', etc.
    operation: Optional[str] = None  # 'buy', 'sell' for add command
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    params: Dict = None


class CommandParser:
    """命令解析器"""
    
    def __init__(self):
        self.commands = {
            'add': self._parse_add_command,
            'delete': self._parse_delete_command,
            'show': self._parse_show_command,
            'status': self._parse_status_command,
            'hedge': self._parse_hedge_command,
            'threshold': self._parse_threshold_command,
            'autohedge': self._parse_autohedge_command,
            'clear': self._parse_clear_command,
            'help': self._parse_help_command,
            'exit': self._parse_exit_command,
            'quit': self._parse_exit_command,
        }
    
    def parse(self, input_text: str) -> Command:
        """
        解析用户输入的命令
        
        Args:
            input_text: 用户输入的命令字符串
            
        Returns:
            Command: 解析后的命令对象
        """
        input_text = input_text.strip().lower()
        
        if not input_text:
            return Command(action='empty')
        
        # 分割命令
        parts = input_text.split()
        action = parts[0]
        
        if action in self.commands:
            return self.commands[action](parts)
        else:
            return Command(action='unknown', params={'input': input_text})
    
    def _parse_add_command(self, parts: List[str]) -> Command:
        """
        解析add命令
        格式: add sell sol-120-c 2
        格式: add buy btc-100000-p 1
        """
        if len(parts) < 4:
            return Command(action='error', params={'message': 'add命令格式错误，正确格式: add [buy|sell] [期权代码] [数量]'})
        
        try:
            operation = parts[1].lower()
            symbol = parts[2].upper()
            quantity = int(parts[3])
            
            if operation not in ['buy', 'sell']:
                return Command(action='error', params={'message': '操作必须是 buy 或 sell'})
            
            if quantity <= 0:
                return Command(action='error', params={'message': '数量必须大于0'})
            
            # 验证期权代码格式 (例: SOL-USD-215-C)
            if not self._validate_option_symbol(symbol):
                return Command(action='error', params={'message': f'期权代码格式错误: {symbol}'})
            
            return Command(
                action='add',
                operation=operation,
                symbol=symbol,
                quantity=quantity
            )
            
        except ValueError:
            return Command(action='error', params={'message': '数量必须是整数'})
    
    def _parse_delete_command(self, parts: List[str]) -> Command:
        """
        解析delete命令
        格式: delete sol-120-c 2
        """
        if len(parts) < 3:
            return Command(action='error', params={'message': 'delete命令格式错误，正确格式: delete [期权代码] [数量]'})
        
        try:
            symbol = parts[1].upper()
            quantity = int(parts[2])
            
            if quantity <= 0:
                return Command(action='error', params={'message': '数量必须大于0'})
            
            if not self._validate_option_symbol(symbol):
                return Command(action='error', params={'message': f'期权代码格式错误: {symbol}'})
            
            return Command(
                action='delete',
                symbol=symbol,
                quantity=quantity
            )
            
        except ValueError:
            return Command(action='error', params={'message': '数量必须是整数'})
    
    def _parse_show_command(self, parts: List[str]) -> Command:
        """
        解析show命令
        格式: show positions
        格式: show orders
        格式: show summary
        """
        if len(parts) < 2:
            return Command(action='show', operation='all')
        
        operation = parts[1].lower()
        valid_operations = ['positions', 'orders', 'summary', 'all']
        
        if operation not in valid_operations:
            return Command(action='error', params={'message': f'show命令参数错误，支持: {", ".join(valid_operations)}'})
        
        return Command(action='show', operation=operation)
    
    def _parse_status_command(self, parts: List[str]) -> Command:
        """
        解析status命令 - 显示实时状态
        """
        return Command(action='status')
    
    def _parse_hedge_command(self, parts: List[str]) -> Command:
        """
        解析hedge命令 - 执行对冲
        格式: hedge
        格式: hedge check (只检查不执行)
        """
        operation = 'execute'  # 默认执行对冲
        
        if len(parts) > 1:
            operation = parts[1].lower()
            if operation not in ['execute', 'check']:
                return Command(action='error', params={'message': 'hedge命令参数错误，支持: execute, check'})
        
        return Command(action='hedge', operation=operation)
    
    def _parse_threshold_command(self, parts: List[str]) -> Command:
        """
        解析threshold命令 - 设置对冲阈值
        格式: threshold 5 (设置为5%)
        格式: threshold (查看当前阈值)
        """
        if len(parts) == 1:
            return Command(action='threshold', operation='show')
        
        try:
            threshold_pct = float(parts[1])
            if threshold_pct <= 0 or threshold_pct > 100:
                return Command(action='error', params={'message': '阈值必须在0-100之间'})
            
            return Command(action='threshold', operation='set', params={'value': threshold_pct / 100})
        except ValueError:
            return Command(action='error', params={'message': '阈值必须是数字(百分比)'})
    
    def _parse_autohedge_command(self, parts: List[str]) -> Command:
        """
        解析autohedge命令 - 控制自动对冲开关
        格式: autohedge on (开启自动对冲)
        格式: autohedge off (关闭自动对冲)
        格式: autohedge status (查看当前状态)
        格式: autohedge (查看当前状态)
        """
        if len(parts) == 1:
            return Command(action='autohedge', operation='status')
        
        operation = parts[1].lower()
        
        if operation in ['on', 'enable', 'start', '开启']:
            return Command(action='autohedge', operation='enable')
        elif operation in ['off', 'disable', 'stop', '关闭']:
            return Command(action='autohedge', operation='disable')
        elif operation in ['status', 'state', '状态']:
            return Command(action='autohedge', operation='status')
        else:
            return Command(action='error', params={'message': 'autohedge命令参数错误，支持: on/off/status'})
    
    def _parse_clear_command(self, parts: List[str]) -> Command:
        """
        解析clear命令 - 清空所有仓位
        """
        return Command(action='clear')
    
    def _parse_help_command(self, parts: List[str]) -> Command:
        """
        解析help命令
        """
        return Command(action='help')
    
    def _parse_exit_command(self, parts: List[str]) -> Command:
        """
        解析exit/quit命令
        """
        return Command(action='exit')
    
    def _validate_option_symbol(self, symbol: str) -> bool:
        """
        验证期权代码格式
        
        Args:
            symbol: 期权代码
            
        Returns:
            bool: 是否有效
        """
        # 期权代码格式: UNDERLYING-USD-STRIKE-TYPE
        # 例: SOL-USD-215-C, BTC-USD-100000-P
        pattern = r'^[A-Z]+-USD-\d+-[CP]$'
        return bool(re.match(pattern, symbol))
    
    def get_help_text(self) -> str:
        """
        获取帮助文本
        
        Returns:
            str: 帮助文本
        """
        return """
对冲程序命令帮助
===============

基本命令:
  add [buy|sell] [期权代码] [数量]    - 添加期权仓位
  delete [期权代码] [数量]            - 平仓期权仓位
  show [positions|orders|summary|all] - 显示仓位信息
  status                             - 显示实时状态和Delta
  
对冲命令:
  hedge                              - 执行自动对冲(检查+下单)
  hedge check                        - 仅检查对冲需求
  threshold [百分比]                  - 设置对冲阈值(如threshold 5)
  threshold                          - 查看当前对冲阈值
  autohedge on/off                   - 开启/关闭自动对冲
  autohedge status                   - 查看自动对冲状态
  
系统命令:
  clear                              - 清空所有仓位记录
  help                               - 显示此帮助信息
  exit/quit                          - 退出程序

命令示例:
  add sell sol-usd-215-c 2          - 卖出2张SOL 215看涨期权
  add buy btc-usd-100000-p 1        - 买入1张BTC 100000看跌期权
  delete sol-usd-215-c 1            - 平仓1张SOL 215看涨期权
  show positions                     - 显示当前期权仓位
  show orders                        - 显示对冲订单历史
  status                             - 显示实时Delta和价格信息
  autohedge on                       - 开启自动对冲功能
  threshold 3                        - 设置3%对冲阈值

期权代码格式:
  格式: [标的]-USD-[行权价]-[类型]
  标的: SOL, BTC, ETH, HYPE 等
  类型: C(看涨期权) 或 P(看跌期权)
  示例: SOL-USD-215-C, BTC-USD-110000-P
"""


def test_parser():
    """测试命令解析器"""
    parser = CommandParser()
    
    test_commands = [
        "add sell sol-usd-215-c 2",
        "add buy btc-usd-100000-p 1",
        "delete sol-usd-215-c 1",
        "show positions",
        "show orders",
        "status",
        "help",
        "invalid command",
        "add sell invalid-symbol 1",
        "add sell sol-usd-215-c abc",
    ]
    
    print("命令解析器测试:")
    print("=" * 50)
    
    for cmd_text in test_commands:
        cmd = parser.parse(cmd_text)
        print(f"输入: {cmd_text}")
        print(f"解析: action={cmd.action}, operation={cmd.operation}, symbol={cmd.symbol}, quantity={cmd.quantity}")
        if cmd.params:
            print(f"参数: {cmd.params}")
        print("-" * 30)


if __name__ == "__main__":
    test_parser()