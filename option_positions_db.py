import sqlite3
from typing import List, Dict, Optional
from paradex_market import ParadexAPI
from logger_config import get_logger

# 获取日志记录器
logger = get_logger(__name__)

class OptionPositionsDB:
    def __init__(self, db_path: str = "option_positions.db"):
        """
        初始化期权仓位数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.paradex_api = ParadexAPI()
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS option_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    delta REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_symbol ON option_positions(symbol)
            ''')
            
            conn.commit()
    
    def _get_option_delta(self, symbol: str) -> Optional[float]:
        """
        从Paradex API获取期权的delta值
        
        Args:
            symbol: 期权合约代码，如 "SOL-USD-215-C"
            
        Returns:
            Optional[float]: delta值，如果获取失败返回None
        """
        try:
            return self.paradex_api.get_option_delta(symbol)
        except Exception as e:
            logger.error(f"获取delta失败: {symbol}, 错误: {e}")
            return None
    
    def add_position(self, symbol: str, quantity: int) -> bool:
        """
        添加期权仓位
        
        Args:
            symbol: 期权合约代码，如 "SOL-USD-215-C"
            quantity: 持仓张数（正数表示多头，负数表示空头）
            
        Returns:
            bool: 添加成功返回True，失败返回False
        """
        if quantity == 0:
            logger.warning("持仓张数不能为0")
            return False
        
        delta = self._get_option_delta(symbol)
        if delta is None:
            logger.error(f"无法获取 {symbol} 的delta值，可能是无效的期权合约")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, quantity FROM option_positions WHERE symbol = ?
                ''', (symbol,))
                
                existing = cursor.fetchone()
                
                if existing:
                    position_id, current_quantity = existing
                    new_quantity = current_quantity + quantity
                    
                    if new_quantity == 0:
                        cursor.execute('''
                            DELETE FROM option_positions WHERE id = ?
                        ''', (position_id,))
                        logger.info(f"已删除 {symbol} 仓位（完全平仓）")
                    else:
                        cursor.execute('''
                            UPDATE option_positions 
                            SET quantity = ?, delta = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (new_quantity, delta, position_id))
                        logger.info(f"已更新 {symbol} 仓位: {current_quantity} -> {new_quantity} 张")
                else:
                    cursor.execute('''
                        INSERT INTO option_positions (symbol, quantity, delta)
                        VALUES (?, ?, ?)
                    ''', (symbol, quantity, delta))
                    logger.info(f"已添加 {symbol} 仓位: {quantity} 张，delta: {delta}")
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {e}")
            return False
    
    def remove_position(self, symbol: str, quantity: int) -> bool:
        """
        减少或删除期权仓位
        
        Args:
            symbol: 期权合约代码
            quantity: 要平仓的张数（正数）
            
        Returns:
            bool: 操作成功返回True，失败返回False
        """
        if quantity <= 0:
            print("平仓张数必须为正数")
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, quantity FROM option_positions WHERE symbol = ?
                ''', (symbol,))
                
                existing = cursor.fetchone()
                
                if not existing:
                    print(f"未找到 {symbol} 的仓位")
                    return False
                
                position_id, current_quantity = existing
                
                if abs(current_quantity) < quantity:
                    print(f"平仓张数 {quantity} 超过当前持仓 {abs(current_quantity)} 张")
                    return False
                
                if current_quantity > 0:
                    new_quantity = current_quantity - quantity
                else:
                    new_quantity = current_quantity + quantity
                
                if new_quantity == 0:
                    cursor.execute('''
                        DELETE FROM option_positions WHERE id = ?
                    ''', (position_id,))
                    print(f"已删除 {symbol} 仓位（完全平仓）")
                else:
                    delta = self._get_option_delta(symbol)
                    cursor.execute('''
                        UPDATE option_positions 
                        SET quantity = ?, delta = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_quantity, delta, position_id))
                    print(f"已更新 {symbol} 仓位: {current_quantity} -> {new_quantity} 张")
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"数据库错误: {e}")
            return False
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        查询特定期权的仓位
        
        Args:
            symbol: 期权合约代码
            
        Returns:
            Optional[Dict]: 仓位信息字典，未找到返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, quantity, delta, created_at, updated_at
                    FROM option_positions WHERE symbol = ?
                ''', (symbol,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'symbol': row[0],
                        'quantity': row[1],
                        'delta': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    }
                return None
                
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return None
    
    def get_all_positions(self) -> List[Dict]:
        """
        查询所有期权仓位
        
        Returns:
            List[Dict]: 所有仓位信息列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, quantity, delta, created_at, updated_at
                    FROM option_positions ORDER BY updated_at DESC
                ''')
                
                rows = cursor.fetchall()
                return [
                    {
                        'symbol': row[0],
                        'quantity': row[1],
                        'delta': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    }
                    for row in rows
                ]
                
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return []
    
    def update_all_deltas(self) -> int:
        """
        更新所有仓位的delta值
        
        Returns:
            int: 成功更新的仓位数量
        """
        positions = self.get_all_positions()
        updated_count = 0
        
        for position in positions:
            symbol = position['symbol']
            new_delta = self._get_option_delta(symbol)
            
            if new_delta is not None:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE option_positions 
                            SET delta = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE symbol = ?
                        ''', (new_delta, symbol))
                        conn.commit()
                        updated_count += 1
                        
                except sqlite3.Error as e:
                    print(f"更新 {symbol} delta失败: {e}")
        
        print(f"已更新 {updated_count} 个仓位的delta值")
        return updated_count
    
    def get_total_delta(self) -> float:
        """
        计算所有仓位的总delta值
        
        Returns:
            float: 总delta值
        """
        positions = self.get_all_positions()
        total_delta = 0.0
        
        for position in positions:
            if position['delta'] is not None:
                total_delta += position['quantity'] * position['delta']
        
        return total_delta
    
    def display_all_positions(self):
        """显示所有仓位的详细信息"""
        positions = self.get_all_positions()
        
        if not positions:
            print("当前没有任何期权仓位")
            return
        
        print(f"当前共有 {len(positions)} 个期权仓位:")
        print("=" * 80)
        
        total_delta = 0.0
        for position in positions:
            symbol = position['symbol']
            quantity = position['quantity']
            delta = position['delta'] or 0.0
            position_delta = quantity * delta
            total_delta += position_delta
            
            print(f"合约: {symbol}")
            print(f"数量: {quantity} 张")
            print(f"Delta: {delta:.4f}")
            print(f"仓位Delta: {position_delta:.4f}")
            print(f"更新时间: {position['updated_at']}")
            print("-" * 40)
        
        print(f"总Delta: {total_delta:.4f}")
        print("=" * 80)
    
    def clear_all_positions(self) -> bool:
        """
        清理数据库中的所有仓位
        
        Returns:
            bool: 清理成功返回True，失败返回False
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM option_positions')
                count = cursor.fetchone()[0]
                
                if count == 0:
                    print("数据库中没有仓位记录")
                    return True
                
                cursor.execute('DELETE FROM option_positions')
                conn.commit()
                
                print(f"已清理 {count} 个仓位记录")
                return True
                
        except sqlite3.Error as e:
            print(f"清理仓位失败: {e}")
            return False

def main():
    """示例用法"""
    db = OptionPositionsDB()
    db.clear_all_positions()
    db.add_position("SOL-USD-215-C", -1)
    db.add_position("HYPE-USD-50-C", -3)
    # db.add_position("SOL-USD-225-C", -1)
    
    db.display_all_positions()
    

    # print("\n平仓后:")
    # db.display_all_positions()
    # # db.clear_all_positions()
    # db.display_all_positions()
if __name__ == "__main__":
    main()