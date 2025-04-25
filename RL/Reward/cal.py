
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
    return max_depth

def get_total_reward(file):
    total_reward = []
    with open(file, 'r', encoding='utf-8') as file:
        for line in file:
            total_reward.append(int(line.strip().split(' ')[8]))
    return total_reward

print('LLM')

print('Original-Reward:', sum(get_total_reward("./rewards_04-23-09.txt")))
print('Original-Depth:', sum(get_max_depth("./rewards_04-23-09.txt")))

print('ABSI-Reward:', sum(get_total_reward("./rewards_04-22-20.txt")))
print('ABSI-Depth:', sum(get_max_depth("./rewards_04-22-20.txt")))

print('DDQN-Reward:', sum(get_total_reward("./rewards_04-22-23.txt")))
print('DDQN-Depth:', sum(get_max_depth("./rewards_04-22-23.txt")))
'''


print('QRASSH-Reward:', sum(get_total_reward("../rewards_03-13-01.txt")))
print('QRASSH-Depth:', sum(get_max_depth("../rewards_03-13-01.txt")))
'''