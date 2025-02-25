import os 
from Enums import Role, GameState

class DisplayAdapter: 
    def __init__(self, player_number: int, total_players: int): 
        self.player_number = player_number 
        self.total_players = total_players

    def update(self, data: dict):
        """清屏并更新显示所有游戏信息"""
        # 清屏
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # 使用颜色美化天数和游戏状态（此处使用亮紫色）
        print(f"\033[95m=== 第 {data['day']} 天 [{data['state']}] ===\033[0m")
        
        # 显示玩家状态，同时如果是 AI 玩家则附带显示其模型名称（用青色突出）
        print("\n玩家状态:")
        for n in range(1, self.total_players + 1):
            if n in data['alivePlayers']:
                status = "\033[92m存活\033[0m"  # 绿色
            else:
                status = "\033[91m死亡\033[0m"  # 红色
            
            # 判断 n 对应的玩家是否为 AI
            ai_info = ""
            if n in data.get("aiPlayers", {}):
                ai = data["aiPlayers"][n]
                ai_info = f" \033[96m[AI: {ai['model_name']}]\033[0m"  # 青色
            print(f"玩家 {n}: {status}{ai_info}")
        
        # 显示玩家自己的角色信息（这里使用黄色突出显示玩家编号和角色）
        print(f"\n你[\033[93m{data['number']}\033[0m]的角色：\033[93m{data['role']}\033[0m")
        if data['role'] == Role.WITCH:
            print(f"解药剩余：{'有' if data['hasSave'] else '无'}")
            print(f"毒药剩余：{'有' if data['hasKill'] else '无'}")
        
        # 显示聊天记录，并为标题添加蓝色
        print("\n\033[94m=== 聊天记录 ===\033[0m")
        for msg in data['chatLog']:
            print(msg)
        print("-" * 20)

    def input(self, prompt: str) -> str:
        """处理用户输入"""
        return input(prompt)
