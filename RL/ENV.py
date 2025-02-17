import gym
from gym import spaces
import numpy as np
from datetime import datetime
from Lifecycle import *

class HoneypotEnv(gym.Env):
    def __init__(self, llm, action_space, date):
        super(HoneypotEnv, self).__init__()
        self.action_space = spaces.Discrete(action_space)  # 定義8個離散動作
        self.observation_space = spaces.Box(low=0, high=1, shape=(203,), dtype=np.float32)
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = []
        self.tactic_buffer = []
        self.max_tactic = 1
        self.histroy = []
        self.date = date

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

        # 執行 command 取得系統輸出
        start = datetime.now()
        system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)
        self.histroy.append(self.command_buffer[0])
        self.histroy.append(system_response)
        del self.command_buffer[0]
        
        self.next_state = np.zeros(self.observation_space.shape[0])
        print('Generate Response time:' + str(datetime.now()-start))

        start = datetime.now()
        ## 如果判斷系統輸出是 honeypot 或沒有下一個 command 就結束
        if self.llm.detect_honeypot_gpt(self.histroy):
            done = True
            self.next_state[-1] = 1
            return self.next_state, -5, done, {}

        elif self.command_buffer == []:
            done = True
            self.next_state[-1] = 1
            return self.next_state, 13, done, {}

        ## 取得下一個 command 的 technique 作為狀態，tactic 作為 reward
        tactic, technique = self.llm.detect_next_state_gpt(action, self.command_buffer[0], self.histroy)
        print('analysis time:' + str(datetime.now()-start))
        print('tactic:', tactic)
        print('technique:', technique)
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic + 1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        return self.next_state, reward, done, {}

    def evaluate(self, action):
        reward = 0
        done = False

        # 從執行 command 取得系統輸出
        start = datetime.now()
        system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)
        self.histroy.append(self.command_buffer[0])
        self.histroy.append(system_response)
        del self.command_buffer[0]
        
        self.next_state = np.zeros(self.observation_space.shape[0])
        print('Generate Response time:' + str(datetime.now()-start))

        start = datetime.now()
        ## 如果判斷系統輸出是 honeypot 或沒有下一個 command 就結束
        if self.llm.detect_honeypot_gpt(self.histroy):
            done = True
            self.next_state[-1] = 1
            return self.next_state, -5, done, {}

        elif self.command_buffer == []:
            done = True
            self.next_state[-1] = 1
            return self.next_state, 13, done, {}

        ## 取得下一個 command 的 technique 作為狀態，tactic 作為 reward
        tactic, technique = self.llm.detect_next_state(action, self.command_buffer[0], self.histroy)
        print('analysis time:' + str(datetime.now()-start))
        print('tactic:', tactic)
        print('technique:', technique)
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic + 1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        return self.next_state, reward, done, {}

    def step_llm(self, action):
        reward = 0
        done = False

        # 從執行 command 取得系統輸出
        start = datetime.now()
        system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)
        self.log_history(action, self.command_buffer[0], system_response)
        self.histroy.append(self.command_buffer[0])
        self.histroy.append(system_response)
        del self.command_buffer[0]
 
        self.next_state = np.zeros(self.observation_space.shape[0])
        print('Generate Response time:' + str(datetime.now()-start))

        start = datetime.now()
        # 如果判斷系統輸出是 honeypot 或沒有下一個 command 就結束
        if self.llm.detect_honeypot_gpt(self.histroy):
            done = True
            self.next_state[-1] = 1
            return self.next_state, -5, done, {}
        
        # 當 command_buffer == null 時，呼叫 LLM 生成 technique
        # Linux 約 111 個 technique
        next_technique = ''
        if self.command_buffer == []:
            while not technique_exist(next_technique):
                next_technique = self.llm.get_next_attack_technique_gpt()
            self.command_buffer = get_command(next_technique)
            print("attack technique:", next_technique)
        
        print('detect or get command time:' + str(datetime.now()-start))
        start = datetime.now()
        ## 取得下一個 command 的 technique 作為狀態，tactic 作為 reward
        tactic, technique = self.llm.detect_next_state_gpt(action, self.command_buffer[0], self.histroy)
        print('analysis time:' + str(datetime.now()-start))
        print('tactic:', tactic)
        print('technique:', technique)
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic + 1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        return self.next_state, reward, done, {}

    def log_history(self, action, command, response):
        with open('interact_{}.txt'.format(self.date), 'a') as f:
            f.write("action:" + action + "\n")
            f.write("command:" + command + "\n")
            f.write("response:" + response + "\n")
            f.write("\n")
