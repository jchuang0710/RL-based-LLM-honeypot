
# Experiment setting
action = 'Engage'   # Engage, ABSI
type = 'RL'   # RL, Original, real system, qrassh
system = 'windows'  # linux, windows
mode = 'train'      # train, test

# RL Hyper parameters
n_hidden = 256
batch_size = 256
lr = 0.001                # learning rate
epsilon = 0.15            # 最初的 epsilon-greedy
eps_min = 0.15            # 最多
eps_decay = 20            # 下降的區間有 100 個
gamma = 0.9               # reward discount factor
target_replace_iter = 10  # target network 更新間隔
memory_capacity = 10000   # 可以儲存多少經驗
train_step = 100          # 多少 step 訓練一次
n_episodes = 5000
warmup_steps = 600

# action setting
if action == 'Engage':
    action_set = ["", "{ Restore to original state }", "{ if output contain network speed, Degrade the network speed }", "{ if output is upload or download, Block this command by the network traffic }", "{ if output contain hardware setting, Change hardware setting }","{ change powershell output this time }","{ if output is file content, Change the file content }", "{ change the output by change the access right }", "{ Block this command this time }"]
elif action == 'ABSI':
    action_set = ["", "{ Block this command this time }", "{ Change output }", "{ Output should contain you are ugly }"]