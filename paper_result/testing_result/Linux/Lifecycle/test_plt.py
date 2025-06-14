
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
def tensorboard_smoothing(values, smooth=0.6):
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

fig, ax1 = plt.subplots(2, 1, figsize=(10, 8))    # a figure with a 2x1 grid of Axes
#print(get_loss("loss_12-19-12.txt"))
bar_width = 0.4

original_reward = "origin_result_12_21_16.txt"
rl_reward = "rl_result_12_22_03.txt"
absi_reward = "absi_result_01_31_16.txt"

ax1[0].bar(np.arange(1, len(get_max_depth(absi_reward)) + 1), get_max_depth(absi_reward), width=bar_width, color="b", label="ABSI")
ax1[0].bar(np.arange(1, len(get_max_depth(rl_reward)) + 1) + bar_width, get_max_depth(rl_reward), width=bar_width, color="r", label="Engage")
ax1[0].set_xlabel("Episode")
ax1[0].set_ylabel("Depth")
ax1[0].set_title("Max Tactic ID of each Episode")
ax1[0].legend(loc = 2)

ax1[1].bar(np.arange(1, len(get_step_efficiency(absi_reward)) + 1), get_step_efficiency(absi_reward), width=bar_width, color="b", label="ABSI")
ax1[1].bar(np.arange(1, len(get_step_efficiency(rl_reward)) + 1) + bar_width, get_step_efficiency(rl_reward), width=bar_width, color="r", label="Engage")
ax1[1].set_xlabel("Episode")
ax1[1].set_ylabel("Step Efficiency")
ax1[1].set_title("Step Efficiency of each Episode")
ax1[1].legend()


ax1[1].legend(loc = 2)

plt.tight_layout()
fig.savefig(fname='./test_result2'+'.png', format='png')
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