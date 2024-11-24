import gym
from gym import spaces
import numpy as np

class HoneypotEnv(gym.Env):
    def __init__(self, llm):
        super(HoneypotEnv, self).__init__()
        self.action_space = spaces.Discrete(8)  # 定義8個離散動作
        self.observation_space = spaces.Box(low=0, high=1, shape=(203,), dtype=np.float32)
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = []
        self.tactic_buffer = []
        self.max_tactic = 1
        self.histroy = []

        self.llm = llm

    def reset(self, lifecycle_command):
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = lifecycle_command
        self.max_tactic = 1
        self.histroy = []
        return self.state

    def step(self, action):
        reward = 0
        done = False

        # 從執行 command 取得系統輸出
        system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)
        self.histroy.append(self.command_buffer[0])
        self.histroy.append(system_response)
        del self.command_buffer[0]
        
        self.next_state = np.zeros(self.observation_space.shape[0])

        ## 如果判斷系統輸出是 honeypot 或沒有下一個 command 就結束
        if self.llm.detect_honeypot(self.histroy):
            done = True
            self.next_state[-1] = 1
            return self.next_state, -5, done, {}

        elif self.command_buffer == []:
            done = True
            self.next_state[-1] = 1
            return self.next_state, 0, done, {}

        ## 取得下一個 command 的 technique 作為狀態，tactic 作為 reward
        tactic, technique = self.llm.next_state(action, self.command_buffer[0], self.histroy)
        print('tactic:', tactic)
        print('technique:', technique)
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic + 1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        return self.next_state, reward, done, {}