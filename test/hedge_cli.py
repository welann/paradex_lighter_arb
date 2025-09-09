#!/usr/bin/env python3
"""
期权对冲管理系统 CLI主程序
整合所有功能模块，提供命令行交互界面
"""

import sys
import asyncio
from command_parser import CommandParser, Command
from position_manager import PositionManager
from display_manager import DisplayManager
from hedge_engine import HedgeEngine


class HedgeCLI:
    """期权对冲管理CLI"""
    
    def __init__(self):
        self.parser = CommandParser()
        self.position_manager = PositionManager()
        self.display_manager = DisplayManager()
        self.hedge_engine = HedgeEngine()
        self.running = True
        self.auto_hedge_enabled = False  # 自动对冲开关
    
    def run(self):
        """运行CLI主循环"""
        print("🚀 启动期权对冲管理系统...")
        
        try:
            # 显示欢迎信息
            self.display_manager.display_welcome()
            
            # 主循环
            while self.running:
                try:
                    # 获取用户输入
                    user_input = input("\n💬 请输入命令 (help 查看帮助): ").strip()
                    
                    if not user_input:
                        continue
                    
                    # 解析命令
                    command = self.parser.parse(user_input)
                    
                    # 执行命令
                    self.execute_command(command)
                    
                except KeyboardInterrupt:
                    print("\n\n⚠️  检测到Ctrl+C，正在退出...")
                    self.running = False
                except EOFError:
                    print("\n\n👋 检测到EOF，正在退出...")
                    self.running = False
                except Exception as e:
                    print(f"❌ 执行命令时出错: {e}")
            
        except Exception as e:
            print(f"❌ 系统错误: {e}")
        finally:
            print("\n👋 感谢使用期权对冲管理系统!")
    
    def execute_command(self, command: Command):
        """
        执行命令
        
        Args:
            command: 解析后的命令对象
        """
        if command.action == 'empty':
            return
        
        elif command.action == 'unknown':
            print(f"❓ 未知命令: {command.params.get('input', '')}")
            print("💡 输入 'help' 查看可用命令")
        
        elif command.action == 'error':
            print(f"❌ {command.params.get('message', '命令错误')}")
        
        elif command.action == 'add':
            self._handle_add_command(command)
        
        elif command.action == 'delete':
            self._handle_delete_command(command)
        
        elif command.action == 'show':
            self._handle_show_command(command)
        
        elif command.action == 'status':
            self._handle_status_command()
        
        elif command.action == 'hedge':
            asyncio.run(self._handle_hedge_command(command))
        
        elif command.action == 'threshold':
            self._handle_threshold_command(command)
        
        elif command.action == 'autohedge':
            self._handle_autohedge_command(command)
        
        elif command.action == 'clear':
            self._handle_clear_command()
        
        elif command.action == 'help':
            self._handle_help_command()
        
        elif command.action == 'exit':
            self._handle_exit_command()
        
        else:
            print(f"❓ 不支持的命令动作: {command.action}")
    
    def _handle_add_command(self, command: Command):
        """处理add命令"""
        try:
            success = self.position_manager.add_position(
                command.symbol, 
                command.operation, 
                command.quantity
            )
            
            if success:
                print(f"\n📊 更新后的仓位汇总:")
                self.display_manager.display_summary_table()
                
                # 如果开启了自动对冲，检查是否需要对冲
                if self.auto_hedge_enabled:
                    print(f"\n🤖 自动对冲已开启，检查对冲需求...")
                    asyncio.run(self._auto_check_hedge())
            
        except Exception as e:
            print(f"❌ 添加仓位失败: {e}")
    
    def _handle_delete_command(self, command: Command):
        """处理delete命令"""
        try:
            success = self.position_manager.remove_position(
                command.symbol, 
                command.quantity
            )
            
            if success:
                print(f"\n📊 更新后的仓位汇总:")
                self.display_manager.display_summary_table()
                
                # 如果开启了自动对冲，检查是否需要对冲
                if self.auto_hedge_enabled:
                    print(f"\n🤖 自动对冲已开启，检查对冲需求...")
                    asyncio.run(self._auto_check_hedge())
            
        except Exception as e:
            print(f"❌ 平仓失败: {e}")
    
    def _handle_show_command(self, command: Command):
        """处理show命令"""
        try:
            operation = command.operation or 'all'
            
            if operation == 'positions':
                self.display_manager.display_positions_table()
            
            elif operation == 'orders':
                self.display_manager.display_orders_table()
            
            elif operation == 'summary':
                self.display_manager.display_summary_table()
            
            elif operation == 'all':
                print("\n📝 期权仓位:")
                self.display_manager.display_positions_table()
                print("\n📊 仓位汇总:")
                self.display_manager.display_summary_table()
                print("\n📋 最近订单:")
                self.display_manager.display_orders_table()
            
        except Exception as e:
            print(f"❌ 显示信息失败: {e}")
    
    def _handle_status_command(self):
        """处理status命令"""
        try:
            # 传递自动对冲状态信息
            self.display_manager.display_realtime_status(
                auto_hedge_enabled=self.auto_hedge_enabled,
                hedge_threshold=self.hedge_engine.hedge_threshold
            )
        except Exception as e:
            print(f"❌ 显示状态失败: {e}")
    
    async def _handle_hedge_command(self, command: Command):
        """处理hedge命令"""
        try:
            operation = command.operation or 'execute'
            
            # 获取当前仓位状态
            status = self.position_manager.get_position_status()
            positions = status['positions']
            delta_summary = status['delta_summary']
            
            if not positions:
                print("📝 当前没有期权仓位，无需对冲")
                return
            
            if operation == 'check':
                # 仅检查对冲需求，不执行
                print(f"\n🔍 对冲需求检查 (阈值: {self.hedge_engine.hedge_threshold*100:.1f}%)")
                recommendations = self.hedge_engine.check_hedge_requirement(delta_summary)
                
                if recommendations:
                    self.hedge_engine.display_hedge_recommendations(recommendations)
                else:
                    print("✅ 当前无需对冲")
            
            elif operation == 'execute':
                # 执行完整的对冲流程
                success = await self.hedge_engine.run_hedge_cycle(positions, delta_summary)
                
                if success:
                    print("\n📊 对冲完成后的仓位状态:")
                    self.display_manager.display_summary_table()
                
        except Exception as e:
            print(f"❌ 处理对冲命令失败: {e}")
    
    def _handle_threshold_command(self, command: Command):
        """处理threshold命令"""
        try:
            operation = command.operation or 'show'
            
            if operation == 'show':
                current = self.hedge_engine.hedge_threshold * 100
                print(f"📊 当前对冲阈值: {current:.1f}%")
                print("💡 当Delta变化超过此阈值时，系统将建议执行对冲")
                
            elif operation == 'set':
                new_threshold = command.params.get('value', 0.05)
                self.hedge_engine.hedge_threshold = new_threshold
                
                print(f"✅ 对冲阈值已设置为: {new_threshold*100:.1f}%")
                
        except Exception as e:
            print(f"❌ 处理阈值命令失败: {e}")
    
    def _handle_autohedge_command(self, command: Command):
        """处理autohedge命令"""
        try:
            operation = command.operation or 'status'
            
            if operation == 'status':
                status = "🟢 开启" if self.auto_hedge_enabled else "🔴 关闭"
                print(f"🤖 自动对冲状态: {status}")
                if self.auto_hedge_enabled:
                    print(f"   对冲阈值: {self.hedge_engine.hedge_threshold*100:.1f}%")
                    print(f"   💡 仓位变动时将自动检查对冲需求")
                else:
                    print(f"   💡 需要手动执行 'hedge' 命令进行对冲")
                    
            elif operation == 'enable':
                self.auto_hedge_enabled = True
                print(f"✅ 自动对冲已开启")
                print(f"   阈值: {self.hedge_engine.hedge_threshold*100:.1f}%")
                print(f"   🚀 仓位变动时将自动检查并提示对冲")
                
            elif operation == 'disable':
                self.auto_hedge_enabled = False
                print(f"❌ 自动对冲已关闭")
                print(f"   💡 如需对冲请手动执行 'hedge' 命令")
                
        except Exception as e:
            print(f"❌ 处理自动对冲命令失败: {e}")
    
    async def _auto_check_hedge(self):
        """自动检查对冲需求"""
        try:
            # 获取当前状态
            status = self.position_manager.get_position_status()
            positions = status['positions']
            delta_summary = status['delta_summary']
            
            if not positions:
                return
            
            # 检查对冲需求
            recommendations = self.hedge_engine.check_hedge_requirement(delta_summary)
            required_hedges = [r for r in recommendations if r.is_required]
            
            if required_hedges:
                print(f"\n⚠️  检测到需要对冲的Delta敞口:")
                for rec in required_hedges:
                    print(f"   🎯 {rec.underlying}: Delta={rec.current_delta:+.6f}, "
                          f"建议{rec.hedge_side} {rec.required_hedge_amount:.4f}")
                
                # 询问用户是否立即执行对冲
                try:
                    confirm = input("\n🤖 是否立即执行自动对冲? [yes/no/later]: ").strip().lower()
                    
                    if confirm in ['yes', 'y', '是']:
                        print(f"\n🚀 执行自动对冲...")
                        success = await self.hedge_engine.run_hedge_cycle(positions, delta_summary)
                        if success:
                            print(f"✅ 自动对冲执行完成")
                        else:
                            print(f"❌ 自动对冲执行失败")
                    elif confirm in ['later', 'l', '稍后']:
                        print(f"📝 已记录对冲需求，稍后可使用 'hedge' 命令执行")
                    else:
                        print(f"❌ 已跳过自动对冲")
                        
                except (KeyboardInterrupt, EOFError):
                    print(f"\n❌ 自动对冲已取消")
            else:
                print(f"✅ Delta敞口在可接受范围内，无需对冲")
                
        except Exception as e:
            print(f"❌ 自动对冲检查失败: {e}")
    
    def _handle_clear_command(self):
        """处理clear命令"""
        try:
            # 确认操作
            confirm = input("⚠️  确认要清空所有仓位记录吗? (yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y', '是']:
                self.position_manager.clear_all_positions()
            else:
                print("❌ 操作已取消")
                
        except Exception as e:
            print(f"❌ 清空仓位失败: {e}")
    
    def _handle_help_command(self):
        """处理help命令"""
        self.display_manager.display_help()
    
    def _handle_exit_command(self):
        """处理exit命令"""
        print("👋 正在退出系统...")
        self.running = False
    
    def display_startup_info(self):
        """显示启动信息"""
        print("\n" + "=" * 60)
        print("🔍 系统自检...")
        
        try:
            # 检查数据库连接
            positions = self.position_manager.db.get_active_option_positions()
            print(f"✅ 数据库连接正常，当前有 {len(positions)} 个活跃仓位")
            
            # 检查API连接
            try:
                markets = self.position_manager.paradex_api.get_option_markets()
                print(f"✅ Paradex API连接正常，获取到 {len(markets)} 个期权")
            except Exception as e:
                print(f"⚠️  Paradex API连接异常: {e}")
            
            try:
                sol_data = self.position_manager.lighter_api.get_market_by_symbol("SOL")
                print(f"✅ Lighter API连接正常，SOL价格: ${sol_data.last_trade_price}")
            except Exception as e:
                print(f"⚠️  Lighter API连接异常: {e}")
            
        except Exception as e:
            print(f"❌ 系统自检失败: {e}")
        
        print("=" * 60)


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    try:
        # 创建并运行CLI
        cli = HedgeCLI()
        cli.display_startup_info()
        cli.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被中断")
    except Exception as e:
        print(f"❌ 程序运行错误: {e}")
    finally:
        print("\n🔚 程序已退出")


if __name__ == "__main__":
    main()