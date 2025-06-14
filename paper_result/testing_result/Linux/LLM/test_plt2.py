
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import numpy as np
def tensorboard_smoothing(values, smooth=0.8):
    smoothed = []
    last = values[0]  # Initialize with the first value
    for value in values:
        smoothed_val = last * smooth + (1 - smooth) * value
        smoothed.append(smoothed_val)
        last = smoothed_val
    return smoothed

def get_loss(file):
    max_depth = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            max_depth.append(float(line.strip().split(' ')[7]))
    return max_depth

def get_max_depth(file):
    max_depth = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            max_depth.append(int(line.strip().split(' ')[12]))
    return max_depth

def get_average_reward(file):
    total_step = get_step(file)
    total_reward = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            total_reward.append(int(line.strip().split(' ')[8]))
    average_reward = []
    
    for index in range(0, len(total_reward)):
        average_reward.append(total_reward[index] / total_step[index])
    return average_reward

def get_total_reward(file):
    total_reward = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            total_reward.append(int(line.strip().split(' ')[8]))
    return total_reward

def get_step(file):
    prev = 0
    total_step = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            total_step.append(int(line.strip().split(' ')[4])-prev)
            prev = int(line.strip().split(' ')[4])
    return total_step

def get_step_efficiency(file):
    prev = 0
    step_efficiency = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            tmp = line.strip().split(' ')
            step_efficiency.append(int(tmp[12]) / (int(tmp[4])-prev))
            prev = int(tmp[4])
    return step_efficiency

episodes = np.arange(1, 3671)
# 第一幅图片：训练的平均长度

original_reward = "rewards_02-23-05.txt"
rl_reward = "rewards_03-08-02.txt"
absi_reward = "rewards_03-10-07.txt"
qrassh = "rewards_03-13-01.txt"

compare = original_reward
# label = "QRASSH"
# label = "ABSI"
label = "Original"
# plasma, inferno, magma
colors = mpl.colormaps['inferno_r'](np.linspace(0, 1, 8))
colors1 = mpl.colormaps['Greys'](np.linspace(0, 1, 8))  # 用 viridis, 自動取色
colors2 = mpl.colormaps['Blues'](np.linspace(0, 1, 8))  # 用 viridis, 自動取色
colors3 = mpl.colormaps['YlGn'](np.linspace(0, 1, 8))  # 用 viridis, 自動取色
colors4 = mpl.colormaps['Reds'](np.linspace(0, 1, 8))  # 用 viridis, 自動取色
colors5 = mpl.colormaps['viridis_r'](np.linspace(0, 1, 8))  # 用 viridis, 自動取色
colors6 = mpl.colormaps['magma_r'](np.linspace(0, 1, 8))  # 用 viridis, 自動取色

fig, ax1 = plt.subplots(2, 1, figsize=(10, 8))    # a figure with a 2x1 grid of Axes
#print(get_loss("loss_12-19-12.txt"))
bar_width = 0.4
font_size = 14  # 調整文字大小
plt.xticks(fontsize=font_size)
plt.yticks(fontsize=font_size)

ax1[0].tick_params(axis='both', labelsize=font_size)
ax1[0].plot(np.arange(1, len(get_max_depth(qrassh)) + 1), tensorboard_smoothing(get_max_depth(qrassh)), linestyle='--', color=colors5[3], label="QRASSH(Cowrie + RL + ABSI)")
ax1[0].plot(np.arange(1, len(get_max_depth(original_reward)) + 1), tensorboard_smoothing(get_max_depth(original_reward)), linestyle=':', color=colors6[3], label="LLM")
ax1[0].plot(np.arange(1, len(get_max_depth(absi_reward)) + 1), tensorboard_smoothing(get_max_depth(absi_reward)), linestyle='-.', color=colors5[1], label="ABSI(LLM + RL + ABSI)")
ax1[0].plot(np.arange(1, len(get_max_depth(rl_reward)) + 1), tensorboard_smoothing(get_max_depth(rl_reward)), color=colors6[7], label="Ours(LLM + RL + Engage)")
ax1[0].set_xlabel("Episode", fontsize=font_size)
ax1[0].set_ylabel("Depth", fontsize=font_size)
ax1[0].set_title("Max Tactic ID of each Episode", fontsize=font_size + 2)
ax1[0].legend(loc=2, fontsize=font_size-4)

ax1[1].tick_params(axis='both', labelsize=font_size)
ax1[1].plot(np.arange(1, len(get_total_reward(qrassh)) + 1), tensorboard_smoothing(get_total_reward(qrassh)), linestyle='--', color=colors5[3], label="QRASSH(Cowrie + RL + ABSI)")
ax1[1].plot(np.arange(1, len(get_total_reward(original_reward)) + 1), tensorboard_smoothing(get_total_reward(original_reward)), linestyle=':', color=colors6[3], label="LLM")
ax1[1].plot(np.arange(1, len(get_total_reward(absi_reward)) + 1), tensorboard_smoothing(get_total_reward(absi_reward)), linestyle='-.', color=colors5[1], label="ABSI(LLM + RL + ABSI)")
ax1[1].plot(np.arange(1, len(get_total_reward(rl_reward)) + 1), tensorboard_smoothing(get_total_reward(rl_reward)), color=colors6[7], label="Ours(LLM + RL + Engage)")
ax1[1].set_xlabel("Episode", fontsize=font_size)
ax1[1].set_ylabel("Reward", fontsize=font_size)
ax1[1].set_title("Total Reward of each Episode", fontsize=font_size + 2)
ax1[1].legend(loc=2, fontsize=font_size-4)


plt.tight_layout()
fig.savefig(fname='./' + 'Attack_Depth_Linux' + '.png', format='png')
plt.show()

# print('Original-Depth:', sum(get_max_depth("rewards_12-16-12.txt")))
# print('DQN-Depth:', sum(get_max_depth("rewards_12-14-03.txt")))
# print('DDQN-Depth:', sum(get_max_depth("rewards_12-14-07.txt")))
# print('DQN-Depth:', sum(get_max_depth("rewards_12-14-17.txt")))
# print('DDQN-Depth:', sum(get_max_depth("rewards_12-18-12.txt")))
# print('Original-Reward:', sum(get_total_reward("rewards_12-21-16.txt")))
# print('Original-Depth:', sum(get_max_depth("rewards_12-21-16.txt")))
# print('DDQN-Reward:', sum(get_total_reward("rewards_12-22-03.txt")))
# print('DDQN-Depth:', sum(get_max_depth("rewards_12-22-03.txt")))

# print('Original-Step Efficiency:', sum(get_max_depth(original_reward))/sum(get_step(original_reward)))
# print('DDQN-Step Efficiency:', sum(get_max_depth(rl_reward))/sum(get_step(rl_reward)))
# print('ABSI-Step Efficiency:', sum(get_max_depth(absi_reward))/sum(get_step(absi_reward)))