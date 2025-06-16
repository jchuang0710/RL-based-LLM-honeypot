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
        # Linux
        self.known_technique = ['T1001.002', 'T1003.007', 'T1003.008', 'T1005', 'T1007', 'T1014', 'T1016.001', 'T1016', 'T1018', 'T1021.004', 'T1027.001', 'T1027.002', 'T1027.004', 'T1027', 'T1030', 'T1033', 'T1036.003', 'T1036.004', 'T1036.005', 'T1036.006', 'T1037.004', 'T1040', 'T1046', 'T1048.002', 'T1048.003', 'T1048', 'T1049', 'T1053.002', 'T1053.003', 'T1053.006', 'T1056.001', 'T1057', 'T1059.004', 'T1059.006', 'T1069.001', 'T1069.002', 'T1070.002', 'T1070.003', 'T1070.004', 'T1070.006', 'T1070.008', 'T1071.001', 'T1074.001', 'T1078.003', 'T1082', 'T1083', 'T1087.001', 'T1087.002', 'T1090.001', 'T1090.003', 'T1098.004', 'T1105', 'T1110.001', 'T1110.004', 'T1113', 'T1115', 'T1124', 'T1132.001', 'T1135', 'T1136.001', 'T1136.002', 'T1140 T1201', 'T1217', 'T1222.002', 'T1485', 'T1486', 'T1489', 'T1496', 'T1497.001', 'T1497.003', 'T1518.001', 'T1529', 'T1531', 'T1543.002', 'T1546.004', 'T1546.005', 'T1547.006', 'T1548.001', 'T1548.003', 'T1552.001', 'T1552.003', 'T1552.004', 'T1552.007', 'T1552', 'T1553.004', 'T1555.003', 'T1556.003', 'T1560.001', 'T1560.002', 'T1562.001', 'T1562.003', 'T1562.004', 'T1562.006', 'T1562.008', 'T1562.010', 'T1562.012', 'T1562', 'T1564.001', 'T1569.002', 'T1571', 'T1574.006', 'T1580', 'T1614.001', 'T1614']
        # Windows
        self.known_technique = ['T1652', 'T1037.001', 'T1136.002', 'T1486', 'T1137', 'T1553.003', 'T1187', 'T1010', 'T1574.011', 'T1218.005', 'T1069.002', 'T1119', 'T1110.002', 'T1201', 'T1036.003', 'T1087.002', 'T1091', 'T1018', 'T1220', 'T1546.008', 'T1557.001', 'T1572', 'T1055.012', 'T1095', 'T1110.004', 'T1040', 'T1003.003', 'T1055.004', 'T1546.011', 'T1222.001', 'T1127.001', 'T1574.002', 'T1027.007', 'T1505.005', 'T1560', 'T1543.003', 'T1072', 'T1053.002', 'T1059.003', 'T1078.003', 'T1090.001', 'T1558.002', 'T1134.004', 'T1114.001', 'T1547.012', 'T1120', 'T1055.011', 'T1547.009', 'T1547.002', 'T1134.001', 'T1090.003', 'T1558.001', 'T1003.004', 'T1112', 'T1574.001', 'T1020', 'T1564', 'T1055.015', 'T1007', 'T1137.004', 'T1222', 'T1574.012', 'T1560.001', 'T1071', 'T1016.001', 'T1059.005', 'T1218.004', 'T1137.006', 'T1562.002', 'T1070.003', 'T1033', 'T1567.003', 'T1573', 'T1055.001', 'T1484.001', 'T1012', 'T1195', 'T1001.002', 'T1489', 'T1070', 'T1071.001', 'T1547.001', 'T1556.002', 'T1567.002', 'T1003.006', 'T1529', 'T1218.011', 'T1005', 'T1106', 'T1482', 'T1552.002', 'T1654', 'T1197', 'T1016', 'T1127', 'T1123', 'T1218.009', 'T1542.001', 'T1559', 'T1563.002', 'T1539', 'T1622', 'T1552.001', 'T1218.003', 'T1497.001', 'T1217', 'T1491.001', 'T1110.003', 'T1547', 'T1574.008', 'T1574.009', 'T1059', 'T1069.001', 'T1546.013', 'T1615', 'T1137.001', 'T1555.003', 'T1559.002', 'T1553.006', 'T1564.003', 'T1070.005', 'T1546.009', 'T1649', 'T1048.002', 'T1569.002', 'T1562.004', 'T1505.003', 'T1027.006', 'T1547.015', 'T1550.002', 'T1055', 'T1553.005', 'T1614', 'T1087.001', 'T1219', 'T1547.003', 'T1553.004', 'T1592.001', 'T1132.001', 'T1113', 'T1027', 'T1057', 'T1218.002', 'T1555.004', 'T1027.004', 'T1485', 'T1564.002', 'T1571', 'T1218.008', 'T1562.001', 'T1036.005', 'T1546.015', 'T1021.003', 'T1082', 'T1030', 'T1055.002', 'T1176', 'T1124', 'T1056.001', 'T1137.002', 'T1552.006', 'T1550.003', 'T1555', 'T1021.002', 'T1083', 'T1546.001', 'T1021.001', 'T1202', 'T1049', 'T1048', 'T1566.001', 'T1216', 'T1564.004', 'T1078.001', 'T1070.001', 'T1136.001', 'T1216.001', 'T1548.002', 'T1204.003', 'T1125', 'T1046', 'T1021.006', 'T1059.007', 'T1620', 'T1614.001', 'T1003.002', 'T1221', 'T1546.010', 'T1218', 'T1039', 'T1547.004', 'T1558.004', 'T1547.008', 'T1134.002', 'T1558.003', 'T1041', 'T1003.001', 'T1564.001', 'T1505.004', 'T1547.006', 'T1129', 'T1218.007', 'T1562', 'T1546', 'T1070.008', 'T1531', 'T1552', 'T1070.006', 'T1006', 'T1490', 'T1546.007', 'T1570', 'T1048.003', 'T1552.004', 'T1135', 'T1003.005', 'T1110.001', 'T1204.002', 'T1207', 'T1505.002', 'T1546.002', 'T1218.001', 'T1562.003', 'T1134.005', 'T1036', 'T1056.004', 'T1016.002', 'T1518']

    def reset(self, lifecycle_command):
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = lifecycle_command
        self.max_tactic = 1
        self.histroy = []
        self.unknown_technique = 0
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
        
            if self.next_technique not in self.known_technique:
                self.unknown_technique = self.unknown_technique + 1
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