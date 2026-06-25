import numpy as np
from datetime import datetime
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.tensorboard import SummaryWriter
# Import setting directly from config to avoid circular import
from src.shared.config import setting
from src.shared.paths import TRAINING_LOGS_DIR, ensure_runtime_directories


class Net(nn.Module):
    """Neural network architecture for Deep Q-Learning"""
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


class BaseDQN(object):
    """Base class for DQN and DDQN algorithms"""
    
    def __init__(self, device, n_states, n_actions):
        self.device = device
        self.n_states = n_states
        self.n_actions = n_actions
        self.n_hidden = setting.n_hidden
        self.batch_size = setting.batch_size
        self.lr = setting.lr
        self.epsilon = setting.epsilon
        self.eps_min = setting.eps_min
        self.eps_decay = setting.eps_decay

        self.gamma = setting.gamma
        self.target_replace_iter = setting.target_replace_iter
        self.memory_capacity = setting.memory_capacity
        
        self.eval_net = self._build_model()
        self.target_net = self._build_model()

        self.memory = np.zeros((setting.memory_capacity, n_states * 2 + 2))  # 每個 memory 中的 experience 大小為 (state + next state + reward + action)
        self.optimizer = torch.optim.Adam(self.eval_net.parameters(), lr=setting.lr)
        
        self.scheduler = ReduceLROnPlateau(self.optimizer, mode='min', factor=0.5, patience=6, min_lr=1e-9)  # 新增基於 Loss 的學習率調整
        self.loss_func = nn.SmoothL1Loss()
        self.memory_counter = 0
        self.learn_step_counter = 0  # 讓 target network 知道什麼時候要更新
        self.loss = 0

        ensure_runtime_directories()
        run_dir = TRAINING_LOGS_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.writer = SummaryWriter(str(run_dir))

    def _build_model(self):
        """Build the neural network model"""
        model = Net(self.n_states, self.n_actions, self.n_hidden).to(self.device)
        return model

    def epsilon_decay(self):
        """Decay epsilon for epsilon-greedy exploration"""
        self.epsilon -= (1 - self.eps_min) / self.eps_decay
        self.epsilon = max(self.epsilon, self.eps_min)

    def choose_action(self, state):
        """Choose action using epsilon-greedy policy"""
        x = torch.unsqueeze(torch.FloatTensor(state), 0).to(self.device)

        # epsilon-greedy
        if np.random.uniform() < self.epsilon:  # 隨機
            action = np.random.randint(0, self.n_actions)
        else:  # 根據現有 policy 做最好的選擇
            actions_value = self.eval_net(x)  # 以現有 eval net 得出各個 action 的分數
            action = torch.max(actions_value, 1)[1].cpu().data.numpy()[0]  # 挑選最高分的 action

        return action

    def store_transition(self, state, action, reward, next_state):
        """Store experience in replay buffer"""
        # 打包 experience
        transition = np.hstack((state, [action, reward], next_state))

        # 存進 memory；舊 memory 可能會被覆蓋
        index = self.memory_counter % self.memory_capacity
        self.memory[index, :] = transition
        self.memory_counter += 1

    def _update_target_network(self):
        """Update target network by copying eval network weights"""
        self.learn_step_counter += 1
        if self.learn_step_counter % self.target_replace_iter == 0:
            self.target_net.load_state_dict(self.eval_net.state_dict())

    def record_loss(self):
        """Record loss to tensorboard"""
        self.writer.add_scalar('Loss/train', self.loss.item(), self.learn_step_counter)

    def print_gap(self, q_eval, q_target):
        """Print Q-value gap to file"""
        with (TRAINING_LOGS_DIR / "q_value_gap.log").open("a", encoding="utf-8") as f:
            f.write(f"Loss: {self.loss.item():.4f}, Q_eval mean: {q_eval.mean().item():.2f}, Q_target mean: {q_target.mean().item():.2f}\n")
    
    def record_reward(self, episode, reward, max_tactic):
        """Record reward to tensorboard"""
        self.writer.add_scalar('Reward/episode', reward, episode)
        self.writer.add_scalar('Depth/episode', max_tactic, episode)

    def evaluate_reward(self, episode, reward, max_tactic):
        """Record evaluation reward to tensorboard"""
        self.writer.add_scalar('Evaluate/reward', reward, episode)
        self.writer.add_scalar('Depth/episode', max_tactic, episode)

    def load(self, name):
        """Load model weights from file"""
        self.eval_net.load_state_dict(torch.load(name, map_location=self.device))

    def save(self, name):
        """Save model weights to file"""
        torch.save(self.eval_net.state_dict(), name)
