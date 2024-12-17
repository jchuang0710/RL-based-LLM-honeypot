import random
import numpy as np
import time
from datetime import datetime
from collections import deque
import os
os.environ["KERAS_BACKEND"] = "torch"
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
#import tensorflow as tf
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.tensorboard import SummaryWriter
#torch.set_grad_enabled(True)

class Net(nn.Module):
    def __init__(self, _input_size: int, _output_size: int, _hidden_size: int = 24):
        super(Net, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(_input_size, _hidden_size),
            nn.ReLU(),
            nn.Linear(_hidden_size, _hidden_size),
            nn.ReLU(),
            nn.Linear(_hidden_size, _output_size)
        )

    def forward(self, x):
        return self.layers(x)

class DQN(object):
    def __init__(self, device, n_states, n_actions, n_hidden, batch_size, lr, epsilon, eps_min, eps_decay, gamma, target_replace_iter, memory_capacity):
        self.device = device
        self.n_states = n_states
        self.n_actions = n_actions
        self.n_hidden = n_hidden
        self.batch_size = batch_size
        self.lr = lr
        self.epsilon = epsilon
        self.eps_min = eps_min
        self.eps_decay = eps_decay

        self.gamma = gamma
        self.target_replace_iter = target_replace_iter
        self.memory_capacity = memory_capacity
        
        self.eval_net = self._build_model()
        self.target_net = self._build_model()

        self.memory = np.zeros((memory_capacity, n_states * 2 + 2)) # 每個 memory 中的 experience 大小為 (state + next state + reward + action)
        self.optimizer = torch.optim.Adam(self.eval_net.parameters(), lr=lr)
        
        self.scheduler = ReduceLROnPlateau(self.optimizer, mode='min', factor=0.5, patience=6, verbose=True, min_lr=1e-6) # 新增基於 Loss 的學習率調整
        self.loss_func = nn.SmoothL1Loss()
        self.memory_counter = 0
        self.learn_step_counter = 0 # 讓 target network 知道什麼時候要更新
        self.loss = 0

        self.writer = SummaryWriter("logs/" + datetime.now().strftime("%m-%d-%H"))

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        model = Net(self.n_states, self.n_actions).to(self.device)
        return model

    def epsilon_decay(self):
        self.epsilon -= (1 - self.eps_min) / self.eps_decay
        self.epsilon = max(self.epsilon, self.eps_min)

    def choose_action(self, state):
        x = torch.unsqueeze(torch.FloatTensor(state), 0).to(self.device)

        # epsilon-greedy
        if np.random.uniform() < self.epsilon: # 隨機
            action = np.random.randint(0, self.n_actions)
        else: # 根據現有 policy 做最好的選擇
            actions_value = self.eval_net(x) # 以現有 eval net 得出各個 action 的分數
            action = torch.max(actions_value, 1)[1].cpu().data.numpy()[0] # 挑選最高分的 action

        return action

    def store_transition(self, state, action, reward, next_state):
        # 打包 experience
        transition = np.hstack((state, [action, reward], next_state))

        # 存進 memory；舊 memory 可能會被覆蓋
        index = self.memory_counter % self.memory_capacity
        self.memory[index, :] = transition
        self.memory_counter += 1

    def learn_DQN(self):
        # 从经验回放中采样
        sample_index = np.random.choice(self.memory_capacity, self.batch_size, replace=False)
        b_memory = self.memory[sample_index, :]
        b_state = torch.FloatTensor(b_memory[:, :self.n_states]).to(self.device)
        b_action = torch.LongTensor(b_memory[:, self.n_states:self.n_states+1].astype(int)).to(self.device)
        b_reward = torch.FloatTensor(b_memory[:, self.n_states+1:self.n_states+2]).to(self.device)
        b_next_state = torch.FloatTensor(b_memory[:, -self.n_states:]).to(self.device)

        # 计算 eval_net 的 Q 值
        q_eval = self.eval_net(b_state).gather(1, b_action)  # eval_net 的 Q 值
        # 计算目标 Q 值时禁用梯度
        torch.set_grad_enabled(False)
        q_next = self.target_net(b_next_state)  # target_net 的 Q 值预测
        q_target = b_reward + self.gamma * q_next.max(1)[0].view(self.batch_size, 1)  # 目标 Q 值
        torch.set_grad_enabled(True)

        # 计算损失
        self.loss = self.loss_func(q_eval, q_target)
        #self.loss = self.loss_func(q_target, q_eval) # 顛倒


        # 反向传播
        self.optimizer.zero_grad()
        self.loss.backward()

        # 添加梯度裁剪
        torch.nn.utils.clip_grad_norm_(self.eval_net.parameters(), max_norm=1.0)

        # 参数更新
        self.optimizer.step()

        # 根据 Loss 调整学习率
        self.scheduler.step(self.loss.item())

        # 每隔 target_replace_iter 次更新 target network
        self.learn_step_counter += 1
        if self.learn_step_counter % self.target_replace_iter == 0:
            self.target_net.load_state_dict(self.eval_net.state_dict())
    
    def learn_DDQN(self):
        # 隨機取樣 batch_size 個 experience
        sample_index = np.random.choice(self.memory_capacity, self.batch_size)
        b_memory = self.memory[sample_index, :]
        b_state = torch.FloatTensor(b_memory[:, :self.n_states]).to(self.device)
        b_action = torch.LongTensor(b_memory[:, self.n_states:self.n_states+1].astype(int)).to(self.device)
        b_reward = torch.FloatTensor(b_memory[:, self.n_states+1:self.n_states+2]).to(self.device)
        b_next_state = torch.FloatTensor(b_memory[:, -self.n_states:]).to(self.device)

        # 計算現有 eval net 和 target net 得出 Q value 的落差
        q_eval = self.eval_net(b_state).gather(1, b_action)  # eval net 所得出的 Q value

        # **DDQN 核心修改**
        # 使用 eval_net 選擇下一步的動作
        torch.set_grad_enabled(False)
        next_action = self.eval_net(b_next_state).max(1)[1].view(self.batch_size, 1)
        
        # 使用 target_net 計算這個動作的 Q 值
        q_next = self.target_net(b_next_state).gather(1, next_action).detach()

        # 計算目標 Q 值
        q_target = b_reward + self.gamma * q_next
        torch.set_grad_enabled(True)
        
        # 計算 loss
        self.loss = self.loss_func(q_eval, q_target)

        # 根據 Loss 調整學習率
        self.scheduler.step(self.loss.item())

        # Backpropagation
        self.optimizer.zero_grad()
        self.loss.backward()
        self.optimizer.step()
        # 每隔一段時間 (target_replace_iter), 更新 target net，即複製 eval net 到 target net
        self.learn_step_counter += 1
        if self.learn_step_counter % self.target_replace_iter == 0:
            self.target_net.load_state_dict(self.eval_net.state_dict())

    def record_loss(self):
        self.writer.add_scalar('Loss/train', self.loss.item(), self.learn_step_counter)
    
    def record_reward(self, episode, reward):
        self.writer.add_scalar('Reward/episode', reward, episode)

    def evaluate_reward(self, episode, reward):
        self.writer.add_scalar('Evaluate/reward', reward, episode)

    def load(self, name):
        self.eval_net.load_state_dict(torch.load(name, map_location=self.device))

    def save(self, name):
        torch.save(self.eval_net.state_dict(), name)