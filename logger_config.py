#!/usr/bin/env python3
"""
统一日志配置模块
使用Loguru提供全局日志管理
"""

import sys
import os
from datetime import datetime
from loguru import logger
from typing import Optional

# 移除默认的handler
logger.remove()

# 全局日志配置
_log_initialized = False
_current_log_file = None

def setup_logger(
    log_level: str = "INFO",
    console_output: bool = True,
    file_output: bool = True,
    log_dir: str = "logs"
) -> str:
    """
    设置全局日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        log_dir: 日志文件目录
        
    Returns:
        str: 日志文件路径
    """
    global _log_initialized, _current_log_file
    
    if _log_initialized:
        return _current_log_file
    
    # 创建日志目录
    if file_output and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成日志文件名
    timestamp = datetime.now().strftime("%Y%m%d")
    log_filename = f"trading_system_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename) if file_output else None
    _current_log_file = log_filepath
    
    # 控制台输出配置
    if console_output:
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            colorize=True
        )
    
    # 文件输出配置
    if file_output:
        logger.add(
            log_filepath,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="100 MB",  # 文件达到100MB时轮转
            retention="30 days",  # 保留30天的日志文件
            compression="zip",   # 压缩旧日志文件
            encoding="utf-8",
            enqueue=True,       # 异步写入，提高性能
            backtrace=True,     # 显示完整错误堆栈
            diagnose=True       # 显示变量值
        )
    
    # 配置第三方库的日志级别
    logger.disable("urllib3")
    logger.disable("requests")
    
    _log_initialized = True
    
    if file_output:
        logger.info(f"日志系统初始化完成，日志文件: {log_filepath}")
    else:
        logger.info("日志系统初始化完成（仅控制台输出）")
    
    return log_filepath

def get_logger(name: str = None):
    """
    获取logger实例
    
    Args:
        name: logger名称，通常使用 __name__
        
    Returns:
        loguru.Logger: logger实例
    """
    if not _log_initialized:
        setup_logger()
    
    if name:
        return logger.bind(name=name)
    return logger

def get_current_log_file() -> Optional[str]:
    """获取当前日志文件路径"""
    return _current_log_file

def log_function_call(func_name: str, **kwargs):
    """记录函数调用"""
    args_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.debug(f"调用函数 {func_name}({args_str})")

def log_performance(func_name: str, duration: float):
    """记录性能信息"""
    logger.info(f"函数 {func_name} 执行耗时: {duration:.3f}秒")

def log_api_call(url: str, method: str = "GET", status_code: int = None, duration: float = None):
    """记录API调用"""
    msg = f"API {method} {url}"
    if status_code:
        msg += f" - 状态码: {status_code}"
    if duration:
        msg += f" - 耗时: {duration:.3f}秒"
    logger.info(msg)

def log_trade_action(action: str, symbol: str, amount: float, price: float = None, success: bool = None):
    """记录交易动作"""
    msg = f"交易动作: {action} {symbol} {amount}"
    if price:
        msg += f" @ ${price:.4f}"
    if success is not None:
        status = "成功" if success else "失败"
        msg += f" - {status}"
    logger.info(msg)

def log_position_change(symbol: str, old_position: float, new_position: float, reason: str = ""):
    """记录仓位变化"""
    change = new_position - old_position
    msg = f"仓位变化: {symbol} {old_position:.4f} -> {new_position:.4f} (变化: {change:+.4f})"
    if reason:
        msg += f" - 原因: {reason}"
    logger.info(msg)

def log_delta_info(symbol: str, delta: float, position: float, target: float):
    """记录Delta对冲信息"""
    logger.info(f"Delta信息: {symbol} - Delta: {delta:.4f}, 当前仓位: {position:.4f}, 目标仓位: {target:.4f}")

# 创建一些常用的logger实例
system_logger = get_logger("system")
trading_logger = get_logger("trading") 
hedge_logger = get_logger("hedge")
api_logger = get_logger("api")
db_logger = get_logger("database")

# 初始化日志系统
if not _log_initialized:
    setup_logger()