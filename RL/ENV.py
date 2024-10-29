import gym
from gym import spaces
import numpy as np

class HoneypotEnv(gym.Env):
    def __init__(self, llm):
        super(HoneypotEnv, self).__init__()
        self.action_space = spaces.Discrete(8)  # 定義8個離散動作
        self.observation_space = spaces.Box(low=0, high=1, shape=(202,), dtype=np.float32)
        self.state = 1
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
        #self.lifecycle = lifecycle
        return self.state

    '''def step(self, action):
        reward = 0
        done = False
        
        if self.histroy == []:
            self.histroy.append('ls')
        
        # 將 action 與 command 送入 LLM honeypot 生成輸出
        system_response = self.llm.answer(action, command, self.histroy)

        # 判斷系統輸出是不是 honeypot
        self.histroy.append(system_response)
        if self.llm.detect_honeypot(self.histroy):
            done = True
            return 0, -1, done, {}
        
        # 如果 command buffer 有東西，就執行下一個 command
        # 沒有就讓 llm 生出下一個 technique 並將 technique map 到 atomic red team 的腳本
        if command_buffer == []:
            technique = _attack_technique()
            if technique == 'exit':
                done = True
                return 0, -1, done, {}

        command = get_command_from_command_buffer()

        # 讓 llm 根據 command 判斷下一個 state
        self.state = self.llm.next_state(command, self.histroy)  
        reward = self.state
        self.histroy.append(command)

        return self.state, reward, done, {}'''

    def step2(self, action):
        reward = 0
        done = False

        # 從 command buffer 取出 command 執行
        #
        system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)
        self.histroy.append(self.command_buffer[0])
        self.histroy.append(system_response)
        #print(self.command_buffer[0])
        #print(system_response)
        del self.command_buffer[0]
        
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[0] = 1
        ## 如果判斷系統輸出是 honeypot 或出現錯誤輸出就結束
        if self.llm.detect_honeypot(self.histroy) or self.command_buffer == []:
            done = True
            return self.next_state, -1, done, {}

        ## 取得下一個 command 的 tactic 作為狀態
        tactic, technique = self.llm.next_state(self.command_buffer[0], self.histroy)
        print('tactic:', tactic)
        print('technique:', technique)
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic+1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        return self.next_state, reward, done, {}

    '''def get_command_set(self, technique):
        pass'''

    '''
    def _next_state(self, action):
        message = self.histroy
        message.append({"role":"user","content": '{please determine the tactic when i input this command "' + command + '"}'})

        Completion = client.chat.completions.create( 
            model="gpt-4o-mini",
            messages=message
        )
        tactic = Completion.choices[0].message.content
        return tactic
    
    def _attack_technique(self, tactic_history, system_response):
        content = ''
        for item in self.histroy:
            if item['role'] == 'user':
                content = content + 'input: ' + item['content'] + '.\n'
            elif item['role'] == 'assistant':
                content = content + 'output: ' + item['content'] + '.\n'

        content = content + ' Please determine the next technique hacker should use according to kill chain. just reply the technique ID, not to explain. If kill chain is end, please reply exit'
        Completion = client.chat.completions.create( 
            model="gpt-4o-mini",
            messages=[ 
                { "role" : "user" , "content" : content }
            ] 
        )
        pass

    def _detect_is_honeypot_or_not(self):
        content = ''
        for item in self.histroy:
            if item['role'] == 'user':
                content = content + 'input: ' + item['content'] + '.\n'
            elif item['role'] == 'assistant':
                content = content + 'output: ' + item['content'] + '.\n'

        content = content + ' Please determine whether these system responses are coming from a honeypot or not. just reply Yes or No, not to explain.'
        Completion = client.chat.completions.create( 
            model="gpt-4o-mini",
            messages=[ 
                { "role" : "user" , "content" : content }
            ] 
        ) 

        if Completion.choices[0].message.content == 'Yes':
            return True
        return False
    
    def _get_command_from_command_buffer(self):
        command = command_buffer[0]
        del command_buffer[0]
        return command

    def _get_system_response(self, action, command):
        self.histroy[-1]['content'] = '{' + action + '} ' + self.histroy[len(self.histroy) -1]['content']
        Completion = client.chat.completions.create( 
            model="gpt-4o-mini",
            messages=self.histroy
        )
        system_response = Completion.choices[0].message.content
        return system_response
    
    '''