import numpy as np
import torch
from src.rl.base import BaseDQN


class DQN(BaseDQN):
    """Deep Q-Network (DQN) implementation"""
    
    def learn(self):
        """
        Train the DQN using experience replay.
        This is the standard DQN learning algorithm.
        """
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

        # 反向传播
        self.optimizer.zero_grad()
        self.loss.backward()

        # 添加梯度裁剪
        torch.nn.utils.clip_grad_norm_(self.eval_net.parameters(), max_norm=1.0)

        # 参数更新
        self.optimizer.step()

        # 根据 Loss 调整学习率
        self.scheduler.step(self.loss.item())

        # 更新 target network
        self._update_target_network()
    
    def learn_DQN(self):
        """Alias for learn() method for backward compatibility"""
        self.learn()
