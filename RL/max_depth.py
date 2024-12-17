
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

def get_max_depth(file):
    max_depth = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            max_depth.append(int(line.strip().split(' ')[12]))
    return max_depth[0:200]

episodes = np.arange(1, 201) 
bar_width = 0.125
# 第一幅图片：训练的平均长度
fig, ax1 = plt.subplots(1, 1)    # a figure with a 2x1 grid of Axes
ax1.bar(episodes - bar_width, get_max_depth("rewards_12-16-12.txt"), width=bar_width, color="g", label="Original")
ax1.bar(episodes, get_max_depth("rewards_12-14-17.txt"), width=bar_width, color="#3399FF", label="DQN")
ax1.bar(episodes + bar_width, get_max_depth("rewards_12-15-02.txt"), width=bar_width, color="#9933FF", label="DDQN")
ax1.set_xlabel("Epsiode")
ax1.set_ylabel("Depth")
ax1.set_title("Max Depth")
ax1.legend()
plt.show()
fig.savefig(fname='./Max_Depth'+'.png', format='png')
print(sum(get_max_depth("rewards_12-16-12.txt")))
print(sum(get_max_depth("rewards_12-14-03.txt")))
print(sum(get_max_depth("rewards_12-14-07.txt")))
print(sum(get_max_depth("rewards_12-14-17.txt")))
print(sum(get_max_depth("rewards_12-15-02.txt")))
