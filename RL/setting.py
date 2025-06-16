
# Experiment setting
action = 'Engage'   # Engage, ABSI
type = 'RL'         # RL, Original, real system, qrassh
system = 'windows'    # linux, windows
mode = 'test'      # train, test

# RL Hyper parameters
n_hidden = 256
batch_size = 256
lr = 0.001                  # learning rate
if mode == 'train':
    epsilon = 1             # 最初的 epsilon-greedy
elif mode == 'test':
    epsilon = 0
eps_min = 0.15              # 最多
eps_decay = 20              # 下降的區間有 100 個
gamma = 0.9                 # reward discount factor
target_replace_iter = 10    # target network 更新間隔
memory_capacity = 10000     # 可以儲存多少經驗
train_step = 100            # 多少 step 訓練一次
warmup_steps = 1000
if mode == 'test':
    n_episodes = 100
elif mode == 'train':
    n_episodes = 5000


# action setting
if action == 'Engage':
    if system == 'linux':
        action_set = ["", "{ Restore to original state }", "{ if output contain network speed, Degrade the network speed }", "{ if output is upload or download, Block this command by the network traffic }", "{ if output contain hardware setting, Change hardware setting }","{ Change terminal output this time }","{ if output is file content, Change the file content }", "{ if output content access right relative, change the access rights }", "{ Block this command this time }"]
    elif system == 'windows':
        action_set = ["","{ allow command execute this time }", "{ Restore to original state }", "{ if response contain network speed, Degrade the network speed }", "{ if response is upload or download, Block this command by the network traffic }", "{ if response contain hardware setting, modify hardware setting }","{ modify powershell response }","{ if response is file content, modify the file content }", "{ modify the response by change the access right }", "{ Block this command this time }"]
elif action == 'ABSI':
    if system == 'linux':
        action_set = ["", "{ Block this command this time }", "{ Change output }", "{ write you are ugly in output}"]
    elif system == 'windows':
        action_set = ["","{ allow command execute this time }", "{ Block this command this time }", "{ modify powershell response }", "{ response should contain you are ugly }"]