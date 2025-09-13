#!/usr/bin/env python3
"""
测试新的统一日志系统
"""

from logger_config import get_logger, get_current_log_file
from option_positions_db import OptionPositionsDB

def test_logging():
    """测试日志功能"""
    logger = get_logger(__name__)
    
    logger.info("开始测试日志系统")
    logger.debug("这是一条调试信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    # 测试数据库日志
    logger.info("测试数据库操作日志...")
    db = OptionPositionsDB()
    
    # 测试添加无效仓位（会触发日志）
    result = db.add_position("INVALID-SYMBOL", 0)
    logger.info(f"添加无效仓位结果: {result}")
    
    # 显示日志文件信息
    log_file = get_current_log_file()
    if log_file:
        logger.info(f"日志文件位置: {log_file}")
        print(f"✅ 日志已写入文件: {log_file}")
        print(f"💡 使用 'tail -f {log_file}' 查看实时日志")
    else:
        print("📝 当前仅控制台输出模式")
    
    logger.info("日志系统测试完成")

if __name__ == "__main__":
    test_logging()