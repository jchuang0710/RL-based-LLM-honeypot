import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
len_mean = pd.read_csv("12-16-12.csv")
DQN_len_mean = pd.read_csv("12-14-17.csv")
DDQN_len_mean = pd.read_csv("12-15-02.csv")
episodes = np.arange(1, 201) 
bar_width = 0.2
# 第一幅图片：训练的平均长度
fig, ax1 = plt.subplots(figsize=(8, 6))    # a figure with a 2x1 grid of Axes
ax1.bar(episodes - bar_width, len_mean['Value'], width=bar_width, color="g", label="Original", align='center')
ax1.bar(episodes + 0.01, DQN_len_mean['Value'], width=bar_width, color="#3399FF", label="DQN", align='center')
ax1.bar(episodes + bar_width + 0.02, DDQN_len_mean['Value'], width=bar_width, color="#9933FF", label="DDQN", align='center')
ax1.set_xlabel("Episode")
ax1.set_ylabel("Reward")
ax1.set_title("Reward × Episode")
ax1.legend()
plt.show()
fig.savefig(fname='./Total_Reward'+'.png', format='png')
print(sum(len_mean['Value'])/200)
print(sum(DQN_len_mean['Value'])/200)
print(sum(DDQN_len_mean['Value'])/200)
