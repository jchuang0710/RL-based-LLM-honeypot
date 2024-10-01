from ENV import HoneypotEnv

env = HoneypotEnv(ChatGPT())

# Environment parameters
n_actions = env.action_space.n
n_states = env.observation_space.shape[0]

print(n_actions)
print(n_states)