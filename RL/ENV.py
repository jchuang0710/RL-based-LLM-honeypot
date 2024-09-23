import gym
from gym import spaces

class HoneypotEnv(gym.Env):
    def __init__(self, llm):
        super(HoneypotEnv, self).__init__()
        self.action_space = spaces.Discrete(8)  # 定義8個離散動作
        self.observation_space = spaces.Box(low=0, high=1, shape=(12,), dtype=np.float32)
        self.state = 1
        self.command_buffer = []
        self.max_tactic = 1
        self.histroy = []

        self.llm = llm

    def reset(self):
        self.state = 1
        self.command_buffer = []
        self.max_tactic = 1
        self.histroy = []
        return self.state

    def step(self, action):
        reward = 0
        done = False
        
        if self.histroy = []:
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

        return self.state, reward, done, {}

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