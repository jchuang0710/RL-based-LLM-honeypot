import numpy as np
import torch
from src.rl.base import BaseDQN


class DDQN(BaseDQN):
    """Double Deep Q-Network (DDQN) implementation"""
    
    def learn(self):
        """
        Train the DDQN using experience replay.
        DDQN uses eval_net to select actions and target_net to evaluate them,
        which reduces overestimation bias compared to standard DQN.
        """
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
        self.print_gap(q_eval, q_target)
        
        # 根據 Loss 調整學習率
        self.scheduler.step(self.loss.item())
        
        # Backpropagation
        self.optimizer.zero_grad()
        self.loss.backward()
        self.optimizer.step()
        
        # 更新 target network
        self._update_target_network()
    
    def learn_DDQN(self):
        """Alias for learn() method for backward compatibility"""
        self.learn()
