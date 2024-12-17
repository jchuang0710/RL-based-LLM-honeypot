import matplotlib.pyplot as plt
import pandas as pd
def tensorboard_smoothing(values, smooth=0.6):
    smoothed = []
    last = values[0]  # Initialize with the first value
    for value in values:
        smoothed_val = last * smooth + (1 - smooth) * value
        smoothed.append(smoothed_val)
        last = smoothed_val
    return smoothed

# 第一幅图片：训练的平均长度
fig, ax1 = plt.subplots(1, 1)    # a figure with a 2x1 grid of Axes
DQN_len_mean = pd.read_csv("12-07-12.csv")
DDQN_len_mean = pd.read_csv("12-09-07.csv")
ax1.plot(DQN_len_mean['Step'], tensorboard_smoothing(DQN_len_mean['Value'], smooth=0.6), color="#3399FF", label="DQN")
ax1.plot(DDQN_len_mean['Step'], tensorboard_smoothing(DDQN_len_mean['Value'], smooth=0.6), color="#9933FF", label="DDQN")
#ax1.set_xticks(np.arange(0, 24, step=2))
ax1.set_xlabel("Steps (x100)")
ax1.set_ylabel("Loss")
ax1.set_title("Training Loss")
ax1.legend()
plt.show()
fig.savefig(fname='./Training-Loss'+'.png', format='png')
