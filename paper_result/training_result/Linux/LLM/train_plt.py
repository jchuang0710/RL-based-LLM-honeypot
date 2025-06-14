
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
# def tensorboard_smoothing(values, smooth=0.99):
#     smoothed = []
#     last = values[0]  # Initialize with the first value
#     for value in values:
#         smoothed_val = last * smooth + (1 - smooth) * value
#         smoothed.append(smoothed_val)
#         last = smoothed_val
#     return smoothed

def tensorboard_smoothing(values: list[float], smooth: float = 0.99) -> list[float]:
    norm_factor = 3
    x = 0
    res: list[float] = []
    for i in range(len(values)):
        x = x * smooth + values[i]  # Exponential decay
        norm_factor *= smooth
        norm_factor += 1
        res.append(x / norm_factor)
    return res

def get_loss(file):
    loss = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            loss.append(float(line.strip().split(' ')[7]))
    return loss

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

def moving_average(data, window_size=10):
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')

font_size = 14  # 調整文字大小
plt.xticks(fontsize=font_size)
plt.yticks(fontsize=font_size)
fig, ax1 = plt.subplots(2, 2, figsize=(12, 8))    # a figure with a 2x1 grid of Axes
#print(get_loss("loss_12-19-12.txt"))
# loss_file = "loss_04-25-10.txt"
# reward_file = "rewards_04-25-10.txt"
loss_file = "training_loss_02-07-04.txt"
reward_file = "training_reward_02-07-04.txt"
ax1[0][0].plot(range(1, len(get_loss(loss_file)) + 1), get_loss(loss_file), color="#FF3030")
ax1[0][0].set_xlabel("Step(x100)", fontsize=font_size)
ax1[0][0].set_ylabel("Loss", fontsize=font_size)
ax1[0][0].set_title("Training Loss", fontsize=font_size+2)
ax1[0][0].legend(fontsize=font_size)

ax1[0][1].plot(range(1, len(get_max_depth(reward_file)) + 1), tensorboard_smoothing(get_max_depth(reward_file)), color="#FF3030")
ax1[0][1].set_xlabel("Episode", fontsize=font_size)
ax1[0][1].set_ylabel("Depth", fontsize=font_size)
ax1[0][1].set_title("Max Tactic ID of each Episode", fontsize=font_size+2)
ax1[0][1].legend(fontsize=font_size)

ax1[1][1].plot(range(1, len(get_step(reward_file)) + 1), tensorboard_smoothing(get_step(reward_file)), color="#FF3030")
ax1[1][1].set_xlabel("Epsiode", fontsize=font_size)
ax1[1][1].set_ylabel("Length", fontsize=font_size)
ax1[1][1].set_title("Session Length of each Episode", fontsize=font_size+2)
ax1[1][1].legend(fontsize=font_size)

ax1[1][0].plot(range(1, len(get_total_reward(reward_file)) + 1), tensorboard_smoothing(get_total_reward(reward_file)), color="#FF3030")
ax1[1][0].set_xlabel("Episode", fontsize=font_size)
ax1[1][0].set_ylabel("Reward", fontsize=font_size)
ax1[1][0].set_title("Reward Trend", fontsize=font_size+2)
ax1[1][0].legend(fontsize=font_size)

plt.tight_layout()
fig.savefig(fname='./training_result'+'.png', format='png')
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