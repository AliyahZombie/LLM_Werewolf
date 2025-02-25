import os
import sys
from enum import Enum
from Enums import Role, GameState
class GameState(Enum):
    NIGHT = 1
    DAY = 2
    VOTE = 3

class DisplayAdapter:
    def __init__(self, player_num: int, total_players: int):
        self.player_num = player_num
        self.total_players = total_players
        self._init_screen_layout()
        self._init_colors()
        
        # 保存最近5条消息
        self.message_buffer = []
        self.status_info = {}
        
    def _init_screen_layout(self):
        """初始化屏幕布局"""
        self.term_width = os.get_terminal_size().columns
        self.term_height = os.get_terminal_size().lines
        
        # 分配垂直空间
        self.header_height = 3
        self.input_height = 2
        self.player_area_height = (self.term_height - self.header_height - self.input_height) // self.total_players
        
        # 计算玩家区域坐标
        self.start_y = self.header_height + (self.player_num-1)*self.player_area_height
        self.end_y = self.start_y + self.player_area_height - 1
        
    def _init_colors(self):
        """初始化颜色配置（ANSI）"""
        self.COLOR_HEADER = "\033[38;5;15m\033[48;5;24m"
        self.COLOR_PLAYER = "\033[38;5;15m\033[48;5;238m"
        self.COLOR_INPUT = "\033[38;5;15m\033[48;5;54m"
        self.RESET = "\033[0m"
        
    def _clear_area(self, start_y: int, end_y: int):
        """清除指定区域内容"""
        for y in range(start_y, end_y+1):
            sys.stdout.write(f"\033[{y};1H\033[K")
        sys.stdout.flush()
        
    def _draw_border(self):
        """绘制玩家区域边框"""
        border = "─" * (self.term_width-2)
        sys.stdout.write(f"\033[{self.start_y};1H\033[37m┌{border}┐{self.RESET}")
        for y in range(self.start_y+1, self.end_y):
            sys.stdout.write(f"\033[{y};1H\033[37m│{self.RESET}")
            sys.stdout.write(f"\033[{y};{self.term_width}H\033[37m│{self.RESET}")
        sys.stdout.write(f"\033[{self.end_y};1H\033[37m└{border}┘{self.RESET}")
        sys.stdout.flush()
        
    def update(self, data: dict):
        """更新显示内容"""
        try:
            # 更新屏幕布局
            self._init_screen_layout()
            
            # 清空原有内容
            self._clear_area(self.start_y+1, self.end_y-1)
            
            # 绘制新内容
            self._draw_header(data)
            self._draw_player_info(data)
            self._draw_messages()
            
        except Exception as e:
            sys.stderr.write(f"Display error: {str(e)}")

    def _draw_header(self, data: dict):
        """绘制公共头信息"""
        header = f" Day {data['day']} | State: {data['state'].name} | Alive: {len(data['alivePlayers'])} "
        sys.stdout.write(f"\033[1;1H{self.COLOR_HEADER}{header.center(self.term_width)}{self.RESET}")
        sys.stdout.flush()

    def _draw_player_info(self, data: dict):
        """绘制玩家状态信息"""
        y = self.start_y + 1
        # 显示玩家编号和角色
        role_str = f"Player {self.player_num} ({data['players'][self.player_num-1].role.name})"
        sys.stdout.write(f"\033[{y};3H{self.COLOR_PLAYER}{role_str}{self.RESET}")
        y += 1
        
        # 显示存活状态
        status = "ALIVE" if data['players'][self.player_num-1].alive else "DEAD"
        sys.stdout.write(f"\033[{y};3H{self.COLOR_PLAYER}Status: {status}{self.RESET}")
        y += 1
        
        # 显示特殊物品
        if hasattr(data['players'][self.player_num-1], 'hasSavePotion'):
            potions = []
            if data['players'][self.player_num-1].hasSavePotion:
                potions.append("💊")
            if data['players'][self.player_num-1].hasKillPotion:
                potions.append("☠️")
            sys.stdout.write(f"\033[{y};3H{self.COLOR_PLAYER}Potions: {' '.join(potions)}{self.RESET}")

    def _draw_messages(self):
        """绘制消息记录"""
        y = self.start_y + 4
        max_lines = self.end_y - y - 1
        for msg in self.message_buffer[-max_lines:]:
            sys.stdout.write(f"\033[{y};3H{self.COLOR_PLAYER}{msg[:self.term_width-4]}{self.RESET}")
            y += 1
            if y >= self.end_y:
                break
                
    def input(self, prompt: str) -> str:
        """显示输入提示并获取输入"""
        try:
            # 定位到输入区域
            input_y = self.term_height - self.input_height + 1
            self._clear_area(input_y, input_y+1)
            
            # 显示带样式的提示
            sys.stdout.write(f"\033[{input_y};1H{self.COLOR_INPUT}{prompt}{self.RESET}")
            sys.stdout.flush()
            
            # 获取输入
            sys.stdout.write(f"\033[{input_y};{len(prompt)+2}H{self.COLOR_INPUT}")
            value = input().strip()
            sys.stdout.write(self.RESET)
            
            # 将输入添加到消息记录
            self.message_buffer.append(f"You > {value}")
            
            return value
        except Exception as e:
            sys.stderr.write(f"Input error: {str(e)}")
            return ""
            
    def add_message(self, sender: str, message: str):
        """添加新消息到缓冲区"""
        self.message_buffer.append(f"{sender} > {message}")
        
# 使用示例
if __name__ == "__main__":
    # 初始化屏幕
    os.system("cls" if os.name == "nt" else "clear")
    sys.stdout.write("\033[?25l")  # 隐藏光标
    
    try:
        # 创建两个玩家的显示适配器
        p1_display = DisplayAdapter(1, 2)
        p2_display = DisplayAdapter(2, 2)
        
        # 模拟更新数据
        dummy_data = {
            "day": 1,
            "state": GameState.NIGHT,
            "alivePlayers": [1,2],
            "players": [
                type("Player", (), {"alive": True, "role": Role.WEREWOLF, "hasSavePotion": False, "hasKillPotion": True}),
                type("Player", (), {"alive": True, "role": Role.VILLAGER, "hasSavePotion": True, "hasKillPotion": False})
            ]
        }
        
        # 更新显示
        p1_display.update(dummy_data)
        p2_display.update(dummy_data)
        
        # 获取输入
        input_value = p1_display.input("Enter your choice:")
        print(f"\nReceived input: {input_value}")
        
    finally:
        sys.stdout.write("\033[?25h")  # 恢复光标显示