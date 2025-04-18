from ENV import HoneypotEnv
from DQN import DQN
from LLM import LLM
from ChatGPT import ChatGPT
from Lifecycle import *
import torch
from datetime import datetime
import os
import setting
torch.set_num_threads(8) 

# date setting
date = datetime.now().strftime("%m-%d-%H")

env = HoneypotEnv(ChatGPT(), len(setting.action_set), date)
# env = HoneypotEnv(LLM("../models/Meta-Llama-3.1-8B-Instruct"), len(action_set), date)

# Environment parameters
n_actions = env.action_space.n
n_states = env.observation_space.shape[0]

# Other parameters
total_step = 0
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)
# 建立 DQN
dqn = DQN(device, n_states, n_actions)
if setting.system == 'linux' and setting.action == 'Engage':
    dqn.load('./model/02-07-04/model_02-07-04_episode_650') # Engage in Linux
elif setting.system == 'linux' and setting.action == 'ABSI':
    dqn.load('./model/02-17-18/model_02-17-18_episode_358') # ABSI in Linux
elif setting.system == 'windows' and setting.action == 'Engage':
    dqn.load('./model/04-14-07/model_04-14-07_episode_732')
elif setting.system == 'windows' and setting.action == 'ABSI':
    pass

# Hacker = Environment
# State = Command's Tactic
# Next_State = Command's Tactic
# Reward = Command's Tactic
# 實際的 Action = LLM Honeypot's Response

# 學習
for i_episode in range(setting.n_episodes):
    print('episode: ',i_episode)
    rewards = 0
    command_set = ['whoami']
    
    if setting.mode == 'qrassh':
        state = env.reset_qrassh(command_set)
    else:
        state = env.reset(command_set)
    
    step = 0

    while True:

        # 從 command set 取出下一個要執行的 command
        # 如果 command set 是空的，則請 LLM 生出下一個要執行的 Technique，並用 ART 轉換成 command set

        print('step: ',step)
        step = step +1
        total_step = total_step + 1

        # 選擇 action
        # state 丟入，回傳 MITRE Engage Action
        action = dqn.choose_action(state)
        # 執行並取得回饋
        ## 送 action + command 給 LLM honeypot，LLM honeypot 送 response 給駭客 ，等駭客回覆 command
        mode_step_fn = {
            'RL': lambda a: env.step_llm(setting.action_set[action]),
            'Original': lambda a: env.step_llm("{ allow command execute this time }"),
            'qrassh': lambda a: env.step_qrassh()
        }

        next_state, reward, done, info = mode_step_fn[setting.type](action)

        # 累積 reward
        rewards += reward
        
        # 儲存 experience
        # 將 state 與 action 給入環境達成的新的 state，紀錄 reward
        # dqn.store_transition(state, action, reward, next_state)

        # # 有足夠 experience 後進行訓練
        # if total_step % train_step == 0: # 儲存 500 個經驗後訓練一次
        #     dqn.learn_DDQN()

        # 進入下一 state
        state = next_state

        if done or step > 50:
            with open('rewards_{}.txt'.format(date), 'a') as f:
                f.write('Episode {} finished after {} steps total rewards {} max tactic id {}\n'.format(i_episode, total_step, rewards, env.max_tactic))
            dqn.record_reward(i_episode, rewards)
            break
        
        #input('next')

env.close()