from ENV import HoneypotEnv
from DQN import DQN
from LLM import LLM
from ChatGPT import ChatGPT
import torch

env = HoneypotEnv(ChatGPT())

# Environment parameters
n_actions = env.action_space.n
n_states = env.observation_space.shape[0]

print(n_actions)
print(n_states)
# Hyper parameters
n_hidden = 50
batch_size = 32
lr = 0.01                 # learning rate
epsilon = 0.1             # epsilon-greedy
gamma = 0.9               # reward discount factor
target_replace_iter = 100 # target network 更新間隔
memory_capacity = 2000
n_episodes = 10000

# 建立 DQN
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#device = "cuda:0"
print(device)
dqn = DQN(device, n_states, n_actions, n_hidden, batch_size, lr, epsilon, gamma, target_replace_iter, memory_capacity)

state = env.reset()
action = dqn.choose_action(state)
print(state)
print(action)