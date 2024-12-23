from ENV import HoneypotEnv
from DQN import DQN
from LLM import LLM
from ChatGPT import ChatGPT
from Lifecycle import *
import torch
from datetime import datetime
torch.set_num_threads(8) 


#env = HoneypotEnv(ChatGPT())
env = HoneypotEnv(LLM("../models/Meta-Llama-3.1-8B-Instruct"))

action_set = ["", "{ Restore to original state }", "{ Degrade the network speed }", "{ Block the network traffic }", "{ Change hardware setting }","{ Change output }","{ Change the file content }", "{ Change the access rights }"]

# Environment parameters
n_actions = env.action_space.n
n_states = env.observation_space.shape[0]

# Other parameters
date = datetime.now().strftime("%m-%d-%H")
warmup_steps = 5000
total_step = 0

# Hyper parameters
n_hidden = 256
batch_size = 256
lr = 0.001               # learning rate
epsilon = 0             # 最初的 epsilon-greedy
eps_min = 0.15            # 最多
eps_decay = 20           # 下降的區間有 100 個
gamma = 0.9               # reward discount factor
target_replace_iter = 10  # target network 更新間隔
memory_capacity = 10000    # 可以儲存多少經驗
train_step = 50          # 多少 step 訓練一次
n_episodes = 200
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)
# 建立 DQN
dqn = DQN(device, n_states, n_actions, n_hidden, batch_size, lr, eps_min, eps_min, eps_decay, gamma, target_replace_iter, memory_capacity)
#dqn.load('./model/model_12-07-12_episode_1797') # DQN
#dqn.load('./model/model_12-09-07_episode_1543') # DDQN
dqn.load('./model/model_12-19-12_episode_3660') # DDQN
# Hacker = Environment
# State = Command's Tactic
# Next_State = Command's Tactic
# Reward = Command's Tactic
# 實際的 Action = LLM Honeypot's Response


# 學習
for i_episode in range(n_episodes):
    print('episode: ',i_episode)
    rewards = 0
    tmp = []
    while tmp == []:
        try:
            tmp = get_lifecycle_command()
        except:
            continue
    state = env.reset(tmp)
    step = 0

    while True:

        print('step: ',step)
        step = step +1
        total_step = total_step + 1

        # 執行並取得回饋
        ## 送 action + command 給 LLM honeypot，LLM honeypot 送 response 給駭客 ，等駭客回覆 command
        #action = dqn.choose_action(state)
        next_state, reward, done, info = env.evaluate(action_set[0])

        # 累積 reward
        rewards += reward

        # 儲存 experience
        # 將 state 與 action 給入環境達成的新的 state，紀錄 reward
        #dqn.store_transition(state, action, reward, next_state)

        #if total_step % train_step == 0: # 儲存一定的經驗後訓練一次
            #dqn.learn_DDQN()

        state = next_state

        if done:
            with open('./Reward/rewards_{}.txt'.format(date), 'a') as f:
                f.write('Episode {} finished after {} steps total rewards {} max tactic id {}\n'.format(i_episode, total_step, rewards, env.max_tactic))
            dqn.evaluate_reward(i_episode, rewards)
            break

env.close()