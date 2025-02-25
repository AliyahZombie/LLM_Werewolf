# main.py
from collections import Counter
import random
import json
import re
import time
from typing import List
import openai
from Enums import Role, GameState
from DisplayAdapter import DisplayAdapter
import json

class LLMPlayerBuilder:
    def __init__(self, config_path: str):
        """
        初始化 LLMPlayerBuilder，读取配置文件中的 API 配置信息。
        
        参数：
            config_path (str): 配置文件的路径（如 'config.json'）
        """
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.api_configs = self.config['api_configs']

    def build_all(self, role: Role):
        """
        使用所有 API 配置构建 LLMPlayer 实例列表。
        
        参数：
            role (Role): 玩家的角色
        
        返回：
            List[LLMPlayer]: 构建好的 LLMPlayer 实例列表
        """
        players = []
        for config in self.api_configs:
            player = LLMPlayer(
                role=role,
                api_base=config['api_base'],
                model_name=config['model_name'],
                api_key=config['api_key']
            )
            players.append(player)
        return players

class Player:
    def __init__(self, role: Role):
        # 将所有属性都作为实例变量初始化，避免多个玩家共享同一状态
        self.role = role
        self.number = 0
        self.alive = True
        self.protected = False
        self.avatar = "./assets/default.png"
        self.display = None
        self.chatLog = []  # 每个玩家独有的聊天记录
        self.hasSavePotion = True
        self.hasKillPotion = True
        self.dataCache = {}

    def requestSpeech(self, prompt) -> str:
        return self.display.input(prompt)

    def updateDisplay(self, data: dict):
        self.display.update(data)
        self.dataCache = data

    def requestVote(self, prompt: str) -> int:
        return int(self.display.input(prompt))

    def updateChat(self, sender: str, message: str):
        self.chatLog.append(f"{sender}: {message}")
        self.updateDisplay(self.dataCache)

    def updateSystem(self, message: str):
        self.updateChat("System", message)
        self.updateDisplay(self.dataCache)

class LLMPlayer(Player):
    def __init__(self, 
                 role: Role,
                 api_base: str,
                 model_name: str,
                 api_key: str,
                 temperature: float = 0.7,
                 max_retries: int = 3):
        super().__init__(role)
        self.api_base = api_base
        self.api_key = api_key
        # 按照你提供的方式初始化OpenAI客户端
        self.client = openai.OpenAI(
            base_url=api_base,
            api_key=api_key
        )
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.memory = []  # 对话记忆

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        alive_players = [str(p.number) for p in self.game.getAlivePlayers()]
        role_desc = {
            Role.WEREWOLF: "你是狼人，夜晚与你的同伴讨论袭击目标，白天伪装成村民",
            Role.VILLAGER: "你是普通村民，通过观察找出狼人",
            Role.SEER: "你是预言家，每晚可以查验一名玩家的身份",
            Role.WITCH: "你是女巫，拥有解药和毒药各一次",
            Role.GUARD: "你是守卫，每晚可以守护一名玩家"
        }
        base_prompt = f"""## 游戏规则
- 当前存活玩家：{', '.join(alive_players)}
- 你的角色：{role_desc[self.role]}
- 你的编号是{self.number}
- 游戏阶段：{self.game.state}
- 禁止暴露角色身份，除非你已经公开身份
- 你收到的内容就是完整的游戏上下文流程和所有玩家发言记录 游戏刚开始时上下文为空时正常的
- 不要胡乱编造
- 用中文回复，保持自然对话语气"""
        
        # 女巫专属提示
        if self.role == Role.WITCH:
            potion_status = []
            if self.hasSavePotion:
                potion_status.append("解药可用")
            if self.hasKillPotion:
                potion_status.append("毒药可用")
            potion_text = " | ".join(potion_status) if potion_status else "无药可用"
            return f"{base_prompt}\n- 当前药水状态：{potion_text}"
        
        return base_prompt

    def _get_game_context(self) -> str:
        """获取聊天记录作为对话上下文"""
        context = self.chatLog
        return "\n".join(context)

    def _call_llm(self, prompt: str) -> str:
        """调用LLM接口（新增流式处理但保持兼容性）"""
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        for _ in range(self.max_retries):
            try:
                # 初始化内容容器
                full_content = ""
                full_reasoning = ""
                
                # 创建流式请求
                stream = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=4096,
                    stream=True  # 启用流式输出
                )
                
                # 实时处理流式响应
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    
                    # 处理思维链内容
                    if getattr(delta, 'reasoning_content', None):
                        full_reasoning += delta.reasoning_content
                        print(f"\033[90m{delta.reasoning_content}\033[0m", end="", flush=True)  # 灰色显示思维链
                    
                    # 处理最终回答内容
                    if getattr(delta, 'content', None):
                        full_content += delta.content
                        print(delta.content, end="", flush=True)  # 正常显示回答内容
                
                print()  # 输出换行
                time.sleep(1)
                return full_content.strip()
                
            except Exception as e:
                print(f"\nAPI Error: {str(e)}")
                print(self.model_name, self.api_base, self.api_key)
                # 重试前清空已收集内容
                full_content = ""
                full_reasoning = ""
                
        return ""  # 维持失败返回空字符串


    def requestSpeech(self, prompt: str) -> str:
        """生成智能发言"""
        full_prompt = f"""## 当前对话
{self._get_game_context()}

## 你的任务
{prompt}
请用1-2句话进行发言，保持自然口语化，不要使用特殊符号"""
        response = self._call_llm(full_prompt)
        # 后处理：移除可能存在的中括号注释，并限制发言长度
        clean_response = re.sub(r"【.*?】", "", response)
        return clean_response[:100]

    def requestVote(self, prompt: str) -> int:
        """智能投票决策"""
        # 女巫解药使用判断
        if "是否使用解药" in prompt and not self.hasSavePotion:
            self.updateSystem("解药已用完")
            return 0  # 自动拒绝使用
        
        # 女巫毒药使用判断
        if "是否使用毒药" in prompt and not self.hasKillPotion:
            self.updateSystem("毒药已用完")
            return -1  # 自动弃权
        
        # 动态修改提示信息
        modified_prompt = prompt
        if self.role == Role.WITCH:
            if "请选择要毒杀的玩家" in prompt:
                if not self.hasKillPotion:
                    self.updateSystem("毒药已不可用")
                    return -1
                modified_prompt = f"{prompt}\n（剩余毒药：{'&radic;' if self.hasKillPotion else '&times;'})"
            if "是否使用解药" in prompt:
                modified_prompt = f"{prompt}\n（剩余解药：{'&radic;' if self.hasSavePotion else '&times;'})"
        
        full_prompt = f"""## 投票规则
{modified_prompt}
请严格按以下格式回复：{{"reason": "分析原因", "vote": 玩家编号或-1}}

## 当前局势
{self._get_game_context()}"""
        response = self._call_llm(full_prompt)
        try:
            if "{" in response:
                json_part = response[response.find("{"):response.find("}")+1]
                data = json.loads(json_part)
                return int(data["vote"])
            else:
                numbers = re.findall(r'\d+', response)
                return int(numbers[-1]) if numbers else -1
        except Exception:
            return -1

    def updateDisplay(self, data: dict):
        """同步游戏状态，不覆盖game对象引用"""
        if self.role == Role.WITCH:
            self.hasSavePotion = data.get("hasSave", True)
            self.hasKillPotion = data.get("hasKill", True)
        # super().updateDisplay(data)

class Game:
    
    def __init__(self, players: List[Player]):
        self.day = 0
        self.dayLog = []
        self.players = players
        self.state = GameState.NIGHT
        self.night_deaths = []  # 用于保存夜间死亡玩家的编号

        total_players = len(players)
        if total_players < 5:
            raise ValueError("游戏需要至少5名玩家")

        # 确定特殊角色配置
        special_roles = [Role.SEER, Role.WITCH]
        if total_players >= 6:
            special_roles.append(Role.GUARD)

        # 计算狼人数量
        max_werewolves = total_players - len(special_roles) - 1  # 至少保留1个村民
        werewolf_count = max(1, min(total_players // 3, max_werewolves))

        # 计算村民数量
        villager_count = total_players - werewolf_count - len(special_roles)
        if villager_count < 1:
            raise ValueError("角色分配失败：村民数量不足")

        # 构建角色列表
        roles = (
            [Role.WEREWOLF] * werewolf_count +
            special_roles +
            [Role.VILLAGER] * villager_count
        )
        random.shuffle(roles)

        # 分配角色和编号
        for i, player in enumerate(players):
            player.number = i + 1
            player.role = roles[i]
            player.game = self  # 绑定游戏实例
            player.alive = True  # 重置存活状态
            player.protected = False
            if hasattr(player, 'last_guarded'):
                player.last_guarded = None  # 重置守卫记忆

        print("角色分配完成：")
        for p in players:
            print(f"玩家 {p.number} 号：{p.role}")

    def checkWin(self) -> bool:
        """检查游戏是否结束"""
        alive_players = self.getAlivePlayers()
        werewolves = [p for p in alive_players if p.role == Role.WEREWOLF]
        villagers = [p for p in alive_players if p.role != Role.WEREWOLF]
        if not werewolves:
            self._broadcast("村民阵营胜利！")
            self.updateDisplay()
            return True
        if len(werewolves) >= len(villagers):
            self._broadcast("狼人阵营胜利！")
            self.updateDisplay()
            return True
        return False

    def getPlayer(self, number: int) -> Player:
        for player in self.players:
            if player.number == number:
                return player
        return None

    def getAlivePlayers(self) -> list:
        return [p for p in self.players if p.alive]

    def getWerewolves(self) -> list:
        return [p for p in self.players if p.role == Role.WEREWOLF]

    def getAliveWerewolves(self) -> list:
        return [p for p in self.getWerewolves() if p.alive]

    def getAliveWitch(self) -> Player:
        witches = [p for p in self.players if p.role == Role.WITCH and p.alive]
        return witches[0] if witches else None

    def getAliveSeers(self) -> list:
        return [p for p in self.players if p.role == Role.SEER and p.alive]

    def getGuards(self) -> list:
        return [p for p in self.players if p.role == Role.GUARD and p.alive]

    def updateDisplay(self):
        for player in self.players:
            data = {
                "day": self.day,
                "state": self.state,
                "alivePlayers": [p.number for p in self.getAlivePlayers()],
                "deadPlayers": [p.number for p in self.players if not p.alive],
                "chatLog": player.chatLog,   # 每个玩家独有的聊天记录
                "role": player.role,
                "hasSave": player.hasSavePotion,
                "hasKill": player.hasKillPotion,
                "aiPlayers": {p.number: {"role": p.role, "model_name": p.model_name}
                          for p in self.players if isinstance(p, LLMPlayer)},
                "number": player.number
            }
            player.updateDisplay(data)

    def _broadcast(self, message: str, role_filter=None):
        """
        广播消息给所有玩家或指定角色：
          - 若role_filter不为空，则只向该角色发送消息；
          - 否则向所有玩家发送。
        """
        recipients = self.players if role_filter is None else [p for p in self.players if p.role == role_filter]
        for p in recipients:
            p.updateSystem(message)

    def _safe_vote(self, player, prompt, valid_targets, allow_abstain=True):
        """安全的投票请求，确保投票结果在允许范围内"""
        while True:
            try:
                vote = player.requestVote(prompt)
                if vote in valid_targets or (allow_abstain and vote == -1):
                    return vote
                player.updateSystem(f"无效目标，请选择：{valid_targets}")
            except ValueError:
                player.updateSystem("请输入有效数字")

    def _resolve_votes(self, votes, action_name, is_public=False):
        """通用投票决议逻辑"""
        valid_votes = [v for v in votes.values() if v != -1]
        if not valid_votes:
            self._broadcast(f"本次{action_name}未达成共识")
            return None
        counter = Counter(valid_votes)
        max_count = counter.most_common(1)[0][1]
        candidates = [num for num, cnt in counter.items() if cnt == max_count]
        if len(candidates) > 1:
            result = random.choice(candidates)
            msg = f"平票！随机选择玩家 {result}"
        else:
            result = candidates[0]
            msg = f"达成共识选择玩家 {result}"
        if is_public:
            self._broadcast(msg)
        else:
            self._broadcast(msg, role_filter=Role.WEREWOLF)
        return result

    def _guard_action(self):
        # 每晚先清除所有玩家的保护状态
        for player in self.players:
            player.protected = False
        self.updateDisplay()
        for guard in self.getGuards():
            candidates = [p.number for p in self.getAlivePlayers()]
            vote = self._safe_vote(
                guard,
                "请选择要守护的玩家（输入玩家编号）",
                valid_targets=candidates,
                allow_abstain=False
            )
            if vote:
                target_player = self.getPlayer(vote)
                target_player.protected = True
                guard.updateSystem(f"你选择守护玩家 {vote}")

    def _werewolf_action(self):
        self.updateDisplay()
        votes = {}
        candidates = [p.number for p in self.getAlivePlayers() if p.role != Role.WEREWOLF]
        # 狼人内部讨论（仅向狼人广播）
        for wolf in self.getAliveWerewolves():
            teammates = [str(p.number) for p in self.getAliveWerewolves() if p != wolf]
            wolf.updateSystem(f"你的队友是：{', '.join(teammates) if teammates else '只有你一人'}")
            speech = wolf.requestSpeech("狼人队伍讨论(仅队友可见) 请发言:")
            self._broadcast(f"🐺 狼人 {wolf.number} 说：{speech}", role_filter=Role.WEREWOLF)
        # 狼人投票
        for wolf in self.getAliveWerewolves():
            self.updateDisplay()
            vote = self._safe_vote(
                wolf,
                f"请选择袭击目标（存活玩家：{candidates}）",
                valid_targets=candidates,
                allow_abstain=False
            )
            votes[wolf.number] = vote
        return self._resolve_votes(votes, "袭击")

    def _witch_action(self, attack_target):
        self.updateDisplay()
        witch = self.getAliveWitch()
        if not witch:
            return
        target_player = self.getPlayer(attack_target)
        # 若目标被守卫保护，则不受伤害
        if target_player.protected:
            witch.updateSystem(f"玩家 {attack_target} 被守卫保护，未受袭击")
            attack_saved = True
        else:
            witch.updateSystem(f"玩家 {attack_target} 正在遭受袭击")
            attack_saved = False
            if witch.hasSavePotion:
                if self._safe_vote(witch, "是否使用解药？（1: 是，0: 否）", [0, 1]) == 1:
                    target_player.alive = True
                    witch.hasSavePotion = False
                    witch.updateSystem(f"你使用了解药拯救玩家 {attack_target}")
                    attack_saved = True
            if not attack_saved:
                target_player.alive = False
                # 不在夜晚直接广播死亡信息，而是记录下来等待天亮时公布
                self.night_deaths.append(attack_target)
        # 女巫毒药行动
        if witch.hasKillPotion:
            valid_targets = [p.number for p in self.getAlivePlayers()] + [-1]
            target = self._safe_vote(
                witch,
                "请选择要毒杀的玩家（-1 表示不使用）",
                valid_targets=valid_targets,
                allow_abstain=True
            )
            if target != -1:
                self.getPlayer(target).alive = False
                witch.hasKillPotion = False
                self.night_deaths.append(target)
                witch.updateSystem(f"你毒杀了玩家 {target}")

    def _seer_action(self):
        self.updateDisplay()
        for seer in self.getAliveSeers():
            target = self._safe_vote(
                seer,
                "请选择要查验的玩家",
                valid_targets=[p.number for p in self.getAlivePlayers()],
                allow_abstain=False
            )
            if target:
                role_info = self.getPlayer(target).role
                seer.updateSystem(f"你查验了玩家 {target} 的身份是：{role_info}")

    def _daytime_discussion(self):
        self.updateDisplay()
        self._broadcast("现在是白天讨论时间")
        for player in self.getAlivePlayers():
            self.updateDisplay()
            speech = player.requestSpeech("请发表你的看法")
            self._broadcast(f"玩家 {player.number} 说：{speech}")

    def _daytime_voting(self):
        votes = {}
        candidates = [p.number for p in self.getAlivePlayers()]
        self.updateDisplay()
        for voter in self.getAlivePlayers():
            vote = self._safe_vote(
                voter,
                f"请选择要放逐的玩家（存活玩家：{candidates}）",
                valid_targets=candidates + [-1],
                allow_abstain=True
            )
            votes[voter.number] = vote
        return self._resolve_votes(votes, "放逐", is_public=True)

    def updateDay(self):
        self.day += 1
        # 夜晚阶段
        self.state = GameState.NIGHT
        # 重置夜间死亡记录
        self.night_deaths = []
        self._guard_action()
        attack_target = self._werewolf_action()
        self._witch_action(attack_target)
        self._seer_action()
        # 白天阶段
        self.state = GameState.DAY
        # 天亮时公布夜间死亡信息
        if self.night_deaths:
            msg = "昨晚死亡玩家：" + ", ".join(str(n) for n in self.night_deaths)
            self._broadcast(msg)
        else:
            self._broadcast("昨晚无人死亡")
        # 清空夜间记录，防止影响下一晚
        self.night_deaths = []
        self._daytime_discussion()
        eliminated = self._daytime_voting()
        if eliminated:
            self._execute_player(eliminated)
        else:
            self._broadcast("今日无人被放逐")
        self.updateDisplay()
        return self.checkWin()

    def _execute_player(self, number):
        player = self.getPlayer(number)
        player.alive = False
        self._broadcast(f"玩家 {number} 被放逐")
        last_words = player.requestSpeech("请发表遗言")
        self._broadcast(f"玩家 {number} 的遗言：{last_words}")

    def main(self):
        for player in self.players:
            player.display = DisplayAdapter(player.number, len(self.players))
        while not self.checkWin():
            self.updateDisplay()
            if self.updateDay():
                break

# 示例用法：仅一个真人玩家，其余均为 AI 玩家
builder = LLMPlayerBuilder('config.json')  # 创建 LLMPlayerBuilder 实例
players = [
    *builder.build_all(None),  # 使用 builder 创建所有 AI 玩家
    Player(None)  # 由真人控制的玩家
]

game = Game(players)
game.main()