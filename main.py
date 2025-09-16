#!/usr/bin/env python3
"""
期权交易和对冲系统命令行界面
提供期权仓位管理和自动对冲功能
"""

import asyncio
from option_positions_db import OptionPositionsDB
from hedge_system import HedgeSystem
from logger_config import get_logger, get_current_log_file

# 获取日志记录器
logger = get_logger(__name__)

class TradingCLI:
    """交易系统命令行界面"""
    
    def __init__(self):
        self.db = OptionPositionsDB()
        self.hedge_system = HedgeSystem(threshold_pct=5.0)
        self.running = True
        self.hedge_task = None  # 用于跟踪后台对冲任务
        self.hedge_thread = None  # 用于跟踪对冲线程
    
    def display_help(self):
        """显示帮助信息"""
        print("\n" + "="*60)
        print("期权交易和对冲系统 - 命令帮助")
        print("="*60)
        print("\n📊 仓位管理命令:")
        print("  add <symbol> <quantity>     - 添加期权仓位")
        print("    示例: add SOL-USD-215-C 5")
        print("  remove <symbol> <quantity>  - 减少期权仓位")
        print("    示例: remove SOL-USD-215-C 2")
        print("  show                        - 显示所有仓位")
        print("  show <symbol>               - 显示特定期权仓位")
        print("  clear                       - 清空所有仓位")
        print("  update                      - 更新所有仓位的delta值")
        print("\n🔄 对冲管理命令:")
        print("  autohedge on                - 开启自动对冲")
        print("  autohedge off               - 关闭自动对冲")
        print("  autohedge status            - 查看自动对冲状态")
        print("  hedge analyze               - 分析对冲需求（不执行交易）")
        print("  hedge execute               - 执行对冲交易")
        print("  threshold <percentage>      - 设置对冲阈值（默认5%）")
        print("  interval <seconds>          - 设置对冲检查间隔（默认60秒，最少10秒）")
        print("\n💡 其他命令:")
        print("  log                         - 显示日志文件路径")
        print("  help                        - 显示此帮助信息")
        print("  quit/exit                   - 退出程序")
        print("="*60)
    
    def display_welcome(self):
        """显示欢迎信息"""
        print("\n🚀 欢迎使用期权交易和对冲系统!")
        print("输入 'help' 查看命令列表，'quit' 退出程序")
        log_file = get_current_log_file()
        if log_file:
            print(f"📝 日志文件: {log_file}")
            print(f"💡 提示: 可以使用 'tail -f {log_file}' 实时查看详细日志\n")
        else:
            print("📝 日志输出: 仅控制台模式\n")
    
    async def handle_add_position(self, parts):
        """处理添加仓位命令"""
        if len(parts) != 3:
            print("❌ 用法: add <symbol> <quantity>")
            print("   示例: add SOL-USD-215-C 5")
            return
        
        symbol = parts[1]
        try:
            quantity = int(parts[2])
            success = self.db.add_position(symbol, quantity)
            if success:
                print(f"✅ 成功添加仓位: {symbol} {quantity}张")
            else:
                print(f"❌ 添加仓位失败: {symbol}")
        except ValueError:
            print("❌ 数量必须是整数")
    
    async def handle_remove_position(self, parts):
        """处理减少仓位命令"""
        if len(parts) != 3:
            print("❌ 用法: remove <symbol> <quantity>")
            print("   示例: remove SOL-USD-215-C 2")
            return
        
        symbol = parts[1]
        try:
            quantity = int(parts[2])
            success = self.db.remove_position(symbol, quantity)
            if success:
                print(f"✅ 成功减少仓位: {symbol} {quantity}张")
            else:
                print(f"❌ 减少仓位失败: {symbol}")
        except ValueError:
            print("❌ 数量必须是正整数")
    
    async def handle_show_positions(self, parts):
        """处理显示仓位命令"""
        if len(parts) == 1:
            # 显示所有仓位
            self.db.display_all_positions()
        elif len(parts) == 2:
            # 显示特定仓位
            symbol = parts[1]
            position = self.db.get_position(symbol)
            if position:
                print(f"\n仓位信息 - {symbol}:")
                print(f"  数量: {position['quantity']}张")
                print(f"  Delta: {position['delta']:.4f}")
                print(f"  仓位Delta: {position['quantity'] * position['delta']:.4f}")
                print(f"  更新时间: {position['updated_at']}")
            else:
                print(f"❌ 未找到期权 {symbol} 的仓位")
        else:
            print("❌ 用法: show 或 show <symbol>")
    
    async def handle_clear_positions(self):
        """处理清空仓位命令"""
        print("⚠️  确定要清空所有仓位吗？这个操作不可撤销！")
        confirm = input("输入 'yes' 确认: ").strip().lower()
        if confirm == 'yes':
            success = self.db.clear_all_positions()
            if success:
                print("✅ 所有仓位已清空")
            else:
                print("❌ 清空仓位失败")
        else:
            print("操作已取消")
    
    async def handle_update_deltas(self):
        """处理更新delta命令"""
        print("📈 正在更新所有仓位的delta值...")
        count = self.db.update_all_deltas()
        print(f"✅ 已更新 {count} 个仓位的delta值")
    
    async def handle_autohedge(self, parts):
        """处理自动对冲命令"""
        if len(parts) != 2:
            print("❌ 用法: autohedge on/off/status")
            return
        
        action = parts[1].lower()
        if action == "on":
            if self.hedge_system.is_auto_hedge_enabled():
                print("⚠️ 自动对冲已经在运行中")
                return
            
            print("✅ 启动自动对冲...")
            print(f"🤖 开始持续对冲监控，每{self.hedge_system.hedge_interval}秒检查一次")
            
            # 使用线程来运行对冲任务，避免阻塞主循环
            import threading
            
            def run_hedge_in_thread():
                """在新线程中运行对冲系统"""
                try:
                    # 创建新的事件循环
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # 运行对冲系统
                    loop.run_until_complete(
                        self.hedge_system.run_hedge_cycle(execute_trades=True, continuous=True)
                    )
                except Exception as e:
                    print(f"❌ 对冲线程出错: {e}")
                    logger.error(f"对冲线程异常: {e}", exc_info=True)
                finally:
                    # 清理
                    try:
                        loop.close()
                    except:
                        pass
            
            # 启动对冲线程
            self.hedge_thread = threading.Thread(target=run_hedge_in_thread, daemon=True)
            self.hedge_thread.start()
            
            # 等待一下确保启动
            import time
            time.sleep(0.5)
            
            if self.hedge_thread.is_alive():
                print("✅ 自动对冲线程已启动并在后台运行")
            else:
                print("❌ 自动对冲线程启动失败")
            
        elif action == "off":
            if not self.hedge_system.is_auto_hedge_enabled():
                print("⚠️ 自动对冲未启动")
                return
                
            print("🛑 正在停止自动对冲...")
            self.hedge_system.stop_auto_hedge()
            
            # 等待线程结束
            if self.hedge_thread and self.hedge_thread.is_alive():
                print("⏳ 等待对冲线程结束...")
                self.hedge_thread.join(timeout=5.0)
                if self.hedge_thread.is_alive():
                    print("⚠️ 对冲线程未能正常结束")
                else:
                    print("✅ 对冲线程已正常结束")
            
            self.hedge_thread = None
            print("❌ 自动对冲已关闭")
            
        elif action == "status":
            is_enabled = self.hedge_system.is_auto_hedge_enabled()
            status = "开启" if is_enabled else "关闭"
            print(f"🔄 自动对冲状态: {status}")
            print(f"📊 对冲阈值: {self.hedge_system.threshold_pct}%")
            print(f"⏰ 检查间隔: {self.hedge_system.hedge_interval}秒")
            
            if is_enabled and self.hedge_thread:
                thread_status = "运行中" if self.hedge_thread.is_alive() else "已停止"
                print(f"🏃 后台线程状态: {thread_status}")
            elif is_enabled:
                print("⚠️ 对冲已启用但线程状态未知")
            else:
                print(f"⭕ 后台线程状态: 未启动")
        else:
            print("❌ 无效选项，请使用: on/off/status")
    
    async def handle_hedge(self, parts):
        """处理对冲命令"""
        if len(parts) != 2:
            print("❌ 用法: hedge analyze/execute")
            return
        
        action = parts[1].lower()
        if action == "analyze":
            print("📊 分析对冲需求...")
            await self.hedge_system.run_hedge_cycle(execute_trades=False)
        elif action == "execute":
            print("⚠️  确定要执行对冲交易吗？")
            confirm = input("输入 'yes' 确认执行实际交易: ").strip().lower()
            if confirm == 'yes':
                print("🔄 执行对冲交易...")
                await self.hedge_system.run_hedge_cycle(execute_trades=True)
            else:
                print("操作已取消")
        else:
            print("❌ 无效选项，请使用: analyze/execute")
    
    async def handle_threshold(self, parts):
        """处理阈值设置命令"""
        if len(parts) != 2:
            print("❌ 用法: threshold <percentage>")
            print("   示例: threshold 3.0")
            return
        
        try:
            threshold = float(parts[1])
            if threshold <= 0 or threshold > 100:
                print("❌ 阈值必须在0-100之间")
                return
            
            self.hedge_system.threshold_pct = threshold
            print(f"✅ 对冲阈值已设置为 {threshold}%")
        except ValueError:
            print("❌ 阈值必须是数字")
    
    async def handle_log_info(self):
        """显示日志文件信息"""
        log_file = get_current_log_file()
        if log_file:
            print(f"\n📝 当前日志文件: {log_file}")
            print(f"💡 实时查看日志: tail -f {log_file}")
            print(f"📊 查看最近日志: tail -n 50 {log_file}")
            
            # 尝试显示日志文件大小
            try:
                import os
                if os.path.exists(log_file):
                    size = os.path.getsize(log_file)
                    if size < 1024:
                        print(f"📁 文件大小: {size} 字节")
                    elif size < 1024 * 1024:
                        print(f"📁 文件大小: {size / 1024:.1f} KB")
                    else:
                        print(f"📁 文件大小: {size / (1024 * 1024):.1f} MB")
                else:
                    print("⚠️ 日志文件尚未创建")
            except Exception as e:
                print(f"⚠️ 无法获取日志文件信息: {e}")
        else:
            print("\n📝 当前运行在控制台日志模式")
            print("💡 日志仅显示在控制台，未写入文件")
    
    async def handle_interval(self, parts):
        """处理对冲间隔设置命令"""
        if len(parts) != 2:
            print("❌ 用法: interval <seconds>")
            print("   示例: interval 30")
            return
        
        try:
            interval = int(parts[1])
            if interval < 1:
                print("❌ 间隔时间不能少于1秒")
                return
            
            self.hedge_system.set_hedge_interval(interval)
            print(f"✅ 对冲检查间隔已设置为 {interval} 秒")
        except ValueError:
            print("❌ 间隔时间必须是整数")
    
    async def process_command(self, command: str):
        """处理用户命令"""
        command = command.strip()
        if not command:
            return
        
        parts = command.split()
        cmd = parts[0].lower()
        
        try:
            if cmd in ['quit', 'exit']:
                print("👋 再见！")
                await self._cleanup_and_exit()
            elif cmd == 'help':
                self.display_help()
            elif cmd == 'add':
                await self.handle_add_position(parts)
            elif cmd == 'remove':
                await self.handle_remove_position(parts)
            elif cmd == 'show':
                await self.handle_show_positions(parts)
            elif cmd == 'clear':
                await self.handle_clear_positions()
            elif cmd == 'update':
                await self.handle_update_deltas()
            elif cmd == 'autohedge':
                await self.handle_autohedge(parts)
            elif cmd == 'hedge':
                await self.handle_hedge(parts)
            elif cmd == 'threshold':
                await self.handle_threshold(parts)
            elif cmd == 'interval':
                await self.handle_interval(parts)
            elif cmd == 'log':
                await self.handle_log_info()
            else:
                print(f"❌ 未知命令: {cmd}")
                print("输入 'help' 查看可用命令")
        except Exception as e:
            print(f"❌ 命令执行出错: {e}")
    
    async def run(self):
        """运行CLI主循环"""
        self.display_welcome()
        
        while self.running:
            try:
                # 显示提示符
                is_hedge_running = (self.hedge_thread and 
                                   self.hedge_thread.is_alive() and 
                                   self.hedge_system.is_auto_hedge_enabled())
                status_indicator = "🟢" if is_hedge_running else "🔴"
                prompt = f"{status_indicator} 期权交易系统> "
                
                # 获取用户输入
                command = input(prompt).strip()
                if command:
                    await self.process_command(command)
                    
            except KeyboardInterrupt:
                print("\n\n👋 程序被用户中断，正在退出...")
                await self._cleanup_and_exit()
            except EOFError:
                print("\n👋 再见！")
                await self._cleanup_and_exit()
            except Exception as e:
                print(f"❌ 系统错误: {e}")
    
    async def _cleanup_and_exit(self):
        """清理资源并退出"""
        self.running = False
        
        # 停止自动对冲
        if self.hedge_system.is_auto_hedge_enabled():
            print("🛑 正在停止自动对冲...")
            self.hedge_system.stop_auto_hedge()
            
            if self.hedge_thread and self.hedge_thread.is_alive():
                print("⏳ 等待对冲线程结束...")
                self.hedge_thread.join(timeout=3.0)
                if self.hedge_thread.is_alive():
                    print("⚠️ 对冲线程未能及时结束")
                else:
                    print("✅ 对冲线程已结束")
            
            self.hedge_thread = None

async def main():
    """主函数"""
    cli = TradingCLI()
    await cli.run()

if __name__ == "__main__":
    asyncio.run(main())

