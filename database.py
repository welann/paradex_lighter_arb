#!/usr/bin/env python3
"""
数据库管理模块
管理Paradex期权仓位和Lighter对冲记录
"""

import sqlite3
import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class OptionPosition:
    """期权仓位数据类"""
    id: Optional[int]
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    entry_time: str
    is_active: bool = True


@dataclass
class HedgeOrder:
    """对冲订单数据类"""
    id: Optional[int]
    platform: str  # 'lighter'
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    order_time: str
    order_hash: Optional[str] = None
    is_filled: bool = False


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "hedge_positions.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库和表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建期权仓位表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_time TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(symbol, side)
            )
        ''')
        
        # 创建对冲订单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hedge_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                order_time TEXT NOT NULL,
                order_hash TEXT,
                is_filled BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_option_symbol ON option_positions(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hedge_symbol ON hedge_orders(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_option_active ON option_positions(is_active)')
        
        conn.commit()
        conn.close()
    
    def add_option_position(self, symbol: str, side: str, quantity: int) -> bool:
        """
        添加期权仓位
        
        Args:
            symbol: 期权代码
            side: 方向 ('buy' or 'sell')
            quantity: 数量
            
        Returns:
            bool: 是否成功添加
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查是否已存在相同仓位
            cursor.execute(
                'SELECT quantity FROM option_positions WHERE symbol = ? AND side = ? AND is_active = TRUE',
                (symbol, side)
            )
            
            existing = cursor.fetchone()
            current_time = datetime.datetime.now().isoformat()
            
            if existing:
                # 更新现有仓位
                new_quantity = existing[0] + quantity
                if new_quantity == 0:
                    # 如果数量为0，标记为不活跃
                    cursor.execute(
                        'UPDATE option_positions SET quantity = 0, is_active = FALSE WHERE symbol = ? AND side = ?',
                        (symbol, side)
                    )
                else:
                    cursor.execute(
                        'UPDATE option_positions SET quantity = ? WHERE symbol = ? AND side = ? AND is_active = TRUE',
                        (new_quantity, symbol, side)
                    )
            else:
                # 插入新仓位
                cursor.execute(
                    'INSERT INTO option_positions (symbol, side, quantity, entry_time) VALUES (?, ?, ?, ?)',
                    (symbol, side, quantity, current_time)
                )
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def delete_option_position(self, symbol: str, quantity: int) -> bool:
        """
        删除期权仓位（平仓）
        
        Args:
            symbol: 期权代码
            quantity: 要平仓的数量
            
        Returns:
            bool: 是否成功删除
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 查找活跃仓位
            cursor.execute(
                'SELECT id, side, quantity FROM option_positions WHERE symbol = ? AND is_active = TRUE',
                (symbol,)
            )
            
            positions = cursor.fetchall()
            if not positions:
                print(f"未找到活跃的 {symbol} 仓位")
                return False
            
            # 简化处理：优先平掉第一个找到的仓位
            pos_id, side, current_quantity = positions[0]
            
            if quantity >= current_quantity:
                # 完全平仓
                cursor.execute(
                    'UPDATE option_positions SET quantity = 0, is_active = FALSE WHERE id = ?',
                    (pos_id,)
                )
                print(f"完全平仓 {symbol} {side} {current_quantity}张")
            else:
                # 部分平仓
                new_quantity = current_quantity - quantity
                cursor.execute(
                    'UPDATE option_positions SET quantity = ? WHERE id = ?',
                    (new_quantity, pos_id)
                )
                print(f"部分平仓 {symbol} {side} {quantity}张，剩余{new_quantity}张")
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def add_hedge_order(self, platform: str, symbol: str, side: str, 
                       quantity: float, price: float, order_hash: str = None) -> bool:
        """
        添加对冲订单记录
        
        Args:
            platform: 交易平台
            symbol: 币种代码
            side: 方向
            quantity: 数量
            price: 价格
            order_hash: 订单哈希
            
        Returns:
            bool: 是否成功添加
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO hedge_orders 
                (platform, symbol, side, quantity, price, order_time, order_hash) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (platform, symbol, side, quantity, price, current_time, order_hash))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return False
        finally:
            conn.close()
    
    def get_active_option_positions(self) -> List[OptionPosition]:
        """获取所有活跃期权仓位"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, symbol, side, quantity, entry_time 
                FROM option_positions 
                WHERE is_active = TRUE AND quantity != 0
                ORDER BY entry_time DESC
            ''')
            
            positions = []
            for row in cursor.fetchall():
                positions.append(OptionPosition(
                    id=row[0],
                    symbol=row[1],
                    side=row[2],
                    quantity=row[3],
                    entry_time=row[4],
                    is_active=True
                ))
            
            return positions
            
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return []
        finally:
            conn.close()
    
    def get_hedge_orders(self, limit: int = 50) -> List[HedgeOrder]:
        """获取对冲订单历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, platform, symbol, side, quantity, price, order_time, order_hash, is_filled
                FROM hedge_orders 
                ORDER BY order_time DESC 
                LIMIT ?
            ''', (limit,))
            
            orders = []
            for row in cursor.fetchall():
                orders.append(HedgeOrder(
                    id=row[0],
                    platform=row[1],
                    symbol=row[2],
                    side=row[3],
                    quantity=row[4],
                    price=row[5],
                    order_time=row[6],
                    order_hash=row[7],
                    is_filled=bool(row[8])
                ))
            
            return orders
            
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return []
        finally:
            conn.close()
    
    def get_position_summary(self) -> Dict[str, Dict]:
        """获取仓位汇总"""
        positions = self.get_active_option_positions()
        summary = {}
        
        for pos in positions:
            # 从期权代码中提取标的资产
            underlying = pos.symbol.split('-')[0]
            
            if underlying not in summary:
                summary[underlying] = {
                    'long_positions': [],
                    'short_positions': [],
                    'total_long': 0,
                    'total_short': 0
                }
            
            if pos.side == 'buy':
                summary[underlying]['long_positions'].append(pos)
                summary[underlying]['total_long'] += pos.quantity
            else:
                summary[underlying]['short_positions'].append(pos)
                summary[underlying]['total_short'] += pos.quantity
        
        return summary
    
    def clear_all_positions(self):
        """清空所有仓位（调试用）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM option_positions')
            cursor.execute('DELETE FROM hedge_orders')
            conn.commit()
            print("所有仓位记录已清空")
        except sqlite3.Error as e:
            print(f"清空失败: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    # 测试数据库功能
    db = DatabaseManager()
    
    print("测试数据库功能...")
    
    # 添加测试仓位
    db.add_option_position("SOL-USD-215-C", "sell", 2)
    db.add_option_position("SOL-USD-200-P", "buy", 1)
    
    # 添加对冲订单
    db.add_hedge_order("lighter", "SOL", "buy", 0.5, 215.50)
    
    # 查看仓位
    positions = db.get_active_option_positions()
    print(f"\n活跃期权仓位: {len(positions)}个")
    for pos in positions:
        print(f"  {pos.symbol} {pos.side} {pos.quantity}张")
    
    # 查看汇总
    summary = db.get_position_summary()
    print(f"\n仓位汇总:")
    for underlying, data in summary.items():
        print(f"  {underlying}: 多头{data['total_long']}张, 空头{data['total_short']}张")
    
    print("\n数据库测试完成!")