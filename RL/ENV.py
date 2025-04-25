import gym
from gym import spaces
import numpy as np
from datetime import datetime
from Lifecycle import *
import paramiko
import time

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
        self.next_technique = ''
        self.llm = llm

    def reset(self, lifecycle_command):
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = lifecycle_command
        self.max_tactic = 1
        self.histroy = []
        return self.state

    def reset_qrassh(self, lifecycle_command):
        self._reconnect_ssh()
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = lifecycle_command
        self.max_tactic = 1
        self.histroy = []
        return self.state

    def _reconnect_ssh(self):
        hostname = "192.168.101.26" # QRASSH
        # hostname = "192.168.101.28" # NCSIST
        port = 2222
        username = "root"
        password = "your_password"  # 或使用密鑰
        host_key_policy = paramiko.AutoAddPolicy()
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname,
            port=port,
            username=username,
            password=password,  # 如果使用密鑰，請移除此行並加上 key_filename 參數
            allow_agent=False,
            look_for_keys=False,
            #disabled_algorithms={"pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]}  # 強制使用 ssh-rsa
        )
        self.shell = self.client.invoke_shell()
        if self.shell.recv_ready():
            self.shell.recv(4096).decode()

    def step_lifecycle(self, action):
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

    def step_llm(self, action):
        reward = 0
        done = False

        # 從執行 command 取得系統輸出
        start = datetime.now()
        system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)
        try:
            self.log_history(action, self.command_buffer[0], system_response)
        except:
            print('log history error')
        self.histroy.append(action + self.command_buffer[0])
        self.histroy.append(system_response)
        del self.command_buffer[0]
 
        print('Generate Response time:' + str(datetime.now()-start))
        self.next_state = np.zeros(self.observation_space.shape[0])
        start = datetime.now()
        # 如果判斷系統輸出是 honeypot 或沒有下一個 command 就結束
        if self.llm.detect_honeypot_gpt(self.histroy):
            done = True
            self.next_state[-1] = 1
            print(self.next_technique)
            return self.next_state, -5, done, {'technique':self.next_technique}
        
        # 當 command_buffer == null 時，呼叫 LLM 生成 technique
        # Linux 約 111 個 technique
        if self.command_buffer == []:
            self.next_technique = ''
            while not technique_exist(self.next_technique):
                self.next_technique = self.llm.get_next_attack_technique_gpt()
            self.command_buffer = get_command(self.next_technique)
            print("attack technique:", self.next_technique)
        
        print('detect or get command time:' + str(datetime.now()-start))
        start = datetime.now()
        ## 取得下一個 command 的 technique 作為狀態，tactic 作為 reward
        tactic, technique = self.llm.detect_next_state_gpt(action, self.command_buffer[0], self.histroy)
        with open('interact/interact_{}.txt'.format(self.date), 'a') as f:
            f.write('tactic:' + str(tactic) + "\n")
            f.write('technique:' + str(technique) + "\n")
            f.write("\n\n")
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
        with open('interact/interact_{}.txt'.format(self.date), 'a') as f:
            f.write("action:" + action + "\n")
            f.write("command:" + command + "\n")
            f.write("response:" + response + "\n")

    def step_qrassh(self):
        reward = 0
        done = False

        # 從執行 command 取得系統輸出
        start = datetime.now()

        #system_response = self.llm.answer(action, self.command_buffer[0], self.histroy)    
        try:
            self.shell.send(self.command_buffer[0] + "\n")
            time.sleep(5)  # 等待命令執行
            system_response = self.shell.recv(4096).decode()  # 讀取輸出
        except OSError as e:
            if "Socket is closed" in str(e):
                print("SSH connection lost. Reconnecting...")
                self._reconnect_ssh()
                self.shell.send(self.command_buffer[0] + "\n")  # 再次發送命令
                time.sleep(5)  # 等待命令執行
                system_response = self.shell.recv(4096).decode()  # 讀取輸出
            else:
                raise e

        self.log_history("", self.command_buffer[0], system_response)
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
            self.shell.close()
            self.client.close()
            return self.next_state, -5, done, {}
        
        # 當 command_buffer == null 時，呼叫 LLM 生成 technique
        # Linux 約 111 個 technique
        next_technique = ''
        if self.command_buffer == []:
            while not technique_exist(next_technique):
                next_technique = self.llm.get_next_attack_technique_gpt()
            self.command_buffer = get_command(next_technique)
            print("next technique:", next_technique)
        
        print('detect or get command time:' + str(datetime.now()-start))
        start = datetime.now()
        ## 取得下一個 command 的 technique 作為狀態，tactic 作為 reward
        tactic, technique = self.llm.detect_next_state_gpt("", self.command_buffer[0], self.histroy)
        print('analysis time:' + str(datetime.now()-start))
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic + 1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        return self.next_state, reward, done, {}