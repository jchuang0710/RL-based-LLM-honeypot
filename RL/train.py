from ENV import HoneypotEnv
from DQN import DQN
from LLM import LLM
from ChatGPT import ChatGPT
import yaml
import os.path
import json
import re
import pandas as pd
import glob
import random
import torch
random.seed(10)

def replace_placeholders(data, input_arguments):
    # 使用正則表達式匹配 #{VAR_NAME} 的樣式
    pattern = re.compile(r'#\{(\w+)\}')
    
    if isinstance(data, dict):
        return {k: replace_placeholders(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_placeholders(v) for v in data]
    elif isinstance(data, str):
        return pattern.sub(lambda match: input_arguments.get(match.group(1), match.group(0)), data)
    else:
        return data

def load_yaml(file_name):
    """Load YAML file to be dict"""
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding="utf-8") as fr:
            dict_obj = yaml.load(fr, Loader=yaml.FullLoader)
        return dict_obj
    else:
        raise FileNotFoundError('NOT Found YAML file %s' % file_name)

def get_technique_command():
    #path = 'C:\\atomic'
    path = '/home/atomic'
    dirPath = '/workspace/LLM-Honeypot/atomic-red-team/atomics/T*/*.yaml'
    file_set = glob.glob(dirPath)
    file_set.sort()

    command_set = ""
    total = 0
    correct = 0
    i=0
    technique_command = {}
    for f in file_set:
        yaml_dict = load_yaml(f)
        flag = False
        for item in yaml_dict['atomic_tests']:
            command_set = []
            if yaml_dict['attack_technique'] not in technique_command:
                technique_command[yaml_dict['attack_technique']] = []
                #print('add:',yaml_dict['attack_technique'])
            if 'linux' in item['supported_platforms']:
                #print(yaml_dict['attack_technique'])
                
                arguments = {}
                #flag = True
                if 'input_arguments' in item:
                    for argument in item['input_arguments']:
                        if type(item['input_arguments'][argument]['default']) != str:
                            arguments[argument] = str(item['input_arguments'][argument]['default'])
                        else:
                            arguments[argument] = item['input_arguments'][argument]['default']
                if 'dependencies' in item:
                    for index in item['dependencies']:
                        
                        '''
                        if 'prereq_command' in index:
                            command = replace_placeholders(index['prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                            command_set.append(command)
                        '''
                        
                        if 'get_prereq_command' in index:
                            command = replace_placeholders(index['get_prereq_command'], arguments).replace('PathToAtomicsFolder', path)
                            tmp = command.split('\n')
                            for i in tmp:
                                if i != '':
                                    command_set.append(i)

                if 'command' in item['executor']:
                    command = replace_placeholders(item['executor']['command'], arguments).replace('PathToAtomicsFolder', path)
                    tmp = command.split('\n')
                    for i in tmp:
                        if i != '':
                            command_set.append(i)
                    #command_set.append(command)

                '''
                if 'cleanup_command' in item['executor']:
                    if item['executor']['cleanup_command']:
                        command = replace_placeholders(item['executor']['cleanup_command'], arguments).replace('PathToAtomicsFolder', path)
                        command_set.append(command)
                '''
            if command_set != []:
                technique_command[yaml_dict['attack_technique']].append(command_set)
    
    return technique_command
            
def get_lifecycle():
    df=pd.read_excel("lifecycle.xlsx")

    # 轉成 numpy.ndarray 格式
    nmp=df.values
    lifecycle = {}
    for item in nmp:
        if item[0] not in lifecycle:
            lifecycle[item[0]] = []
        lifecycle[item[0]].append(item[1])

    return lifecycle

# 取得一個 lifecycle 所使用的 command
def get_lifecycle_command():
    # 取得所有的 lifecycle
    lifecycle_set = get_lifecycle()
    # 取得所有的 technique 所使用的 procedure
    technique_command = get_technique_command()
    lifecycle_command = []
    # 隨機選一個 lifecycle
    for technique in lifecycle_set[random.choice(list(lifecycle_set.keys()))]:
        if technique in technique_command and technique_command[technique] != []:
            # 隨機選一個 procedure
            for command in random.choice(technique_command[technique]):
                lifecycle_command.append(command)
    return lifecycle_command

env = HoneypotEnv(ChatGPT())

action_set = ["{ allow command execution }", "{ Restore to original state }", "{ Degrade the network speed }", "{ Block the network traffic }", "{ Change hardware setting }","{ Change output }","{ Change the file content }", "{ Change the access rights }"]

# Environment parameters
n_actions = env.action_space.n
n_states = env.observation_space.shape[0]

# Hyper parameters
n_hidden = 50
batch_size = 32
lr = 0.01                 # learning rate
epsilon = 0.1             # epsilon-greedy
gamma = 0.9               # reward discount factor
target_replace_iter = 100 # target network 更新間隔
memory_capacity = 2000
n_episodes = 10000
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(device)
# 建立 DQN
dqn = DQN(device, n_states, n_actions, n_hidden, batch_size, lr, epsilon, gamma, target_replace_iter, memory_capacity)


# Hacker = Environment
# State = Command's Tactic
# Next_State = Command's Tactic
# Reward = Command's Tactic
# 實際的 Action = LLM Honeypot's Response


# 學習
for i_episode in range(n_episodes):
    print(i_episode)
    t = 0
    rewards = 0
    tmp = get_lifecycle_command()
    while tmp == []:
        tmp = get_lifecycle_command()
    state = env.reset(tmp)

    while True:

        # 可視化環境
        # env.render()

        # 選擇 action
        # state 丟入，回傳 MITRE Engage Action
        action = dqn.choose_action(state)

        # 執行並取得回饋
        ## 送 action + command 給 LLM honeypot，LLM honeypot 送 response 給駭客 ，等駭客回覆 command
        next_state, reward, done, info = env.step2(action_set[action])

        # 儲存 experience
        # 將 state 與 action 給入環境達成的新的 state，紀錄 reward
        #print(state, action, reward, next_state)
        rewards += reward
        
        # 累積 reward
        if rewards != -1:
            dqn.store_transition(state, action, reward, next_state)
            # 有足夠 experience 後進行訓練
            if dqn.memory_counter > memory_capacity:
                dqn.learn()

            # 進入下一 state
            state = next_state

            if done:
                dqn.learn()
                with open('rewards.txt', 'a') as f:
                    f.write('Episode {} finished after {} timesteps, loss {}, total rewards {} max tactic id {}\n'.format(i_episode, t+1, dqn.loss, rewards, env.max_tactic))
                if i_episode % 100 == 99:
                    dqn.save('model_{}_episode_{}'.format('10/17', i_episode))
                break

            t += 1
        else:
            break
        
        #input('next')

env.close()