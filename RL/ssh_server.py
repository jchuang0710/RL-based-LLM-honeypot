import socket, sys, threading
import paramiko
from datetime import datetime
import torch
from DQN import DQN
import numpy as np
import setting
import time

# Generate keys with 'ssh-keygen -t rsa -f server.key'
HOST_KEY = paramiko.RSAKey(filename='server.key')
SSH_PORT = 2222

# Log the user:password combinations to files
LOGFILE = 'logs/auth.log' 
LOGFILE_LOCK = threading.Lock()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#device = 'cpu'
print(device)
# 建立 DQN
n_actions = len(setting.action_set)
n_states = 203

dqn = DQN(device, n_states, n_actions)
if setting.system == 'linux' and setting.action == 'Engage':
    dqn.load('./model/02-07-04/model_02-07-04_episode_650') # Engage in Linux
    # dqn.load('./model/05-02-00/model_05-02-00_episode_352') # 有負 reward
elif setting.system == 'linux' and setting.action == 'ABSI':
    dqn.load('./model/02-17-18/model_02-17-18_episode_468') # ABSI in Linux
elif setting.system == 'windows' and setting.action == 'Engage':
    dqn.load('./model/04-21-14/model_04-21-14_episode_847')
elif setting.system == 'windows' and setting.action == 'ABSI':
    dqn.load('./model/04-18-17/model_04-18-17_episode_722')


class SSHServerHandler(paramiko.ServerInterface):
    def __init__(self, llm_model):
        self.event = threading.Event()
        self.llm_model = llm_model
        self.log_history = []
        self.action_set = setting.action_set
        self.dpn = dqn

    def check_channel_request(self, kind, channelID): 
        return paramiko.OPEN_SUCCEEDED
    
    def check_channel_shell_request(self, channel): 
        print("Channel", channel) 
        self.channel = channel
        return True
    
    def check_channel_pty_request(self, c, t, w, h, p, ph, m): 
        return True
    
    def get_allowed_auths(self, username):
        return 'password'
    
    def check_auth_password(self, username, password):
        self.username = username
        self.password = password
        self.llm_model.add_system_prompt('user-name=' + self.username + ' passowrd=' + self.password + '.')
        # save login info to a file
        LOGFILE_LOCK.acquire()
        try:
            logfile_handle = open(LOGFILE,"a")
            print("New login: " + username + ":" + password)
            logfile_handle.write(username + ":" + password + "\n")
            logfile_handle.close()
        finally:
            LOGFILE_LOCK.release()

        return paramiko.AUTH_SUCCESSFUL
    
    def handle_shell(self):
        log_filename = f"real_time_logs/log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        response = self.llm_model.answer(self.action_set[0], '\n', self.log_history)
        self.channel.sendall(f'{response}')
        self.log_history.append('\n')
        self.log_history.append(response)
        while not self.channel.exit_status_ready():
            try:
                # Receive user input
                # self.channel.sendall(f'{self.username}@localhost:~/ $')
                command = self.channel.recv(1024).decode("utf-8").strip()
                
                print("CMD:", command)
                if command == 'exit' or command == 'logout':
                    break
                start = datetime.now()
                tactic_id, technique_id = self.llm_model.detect_next_state_gpt(command, self.log_history)
                log_file = open(log_filename, "a")
                log_file.write(f"Detection Time: {datetime.now()- start}\n")
                log_file.close()
                state = np.zeros(n_states)
                state[technique_id-1] = 1

                action = dqn.choose_action(state)
                print("action:", self.action_set[action])
                # Produce output with LLM
                start = datetime.now()
                response = self.llm_model.answer(self.action_set[action], command, self.log_history)
                log_file = open(log_filename, "a")
                log_file.write(f"Generate Response Time: {datetime.now()- start}\n")
                log_file.close()
                print(response)
                
                # Save the logs
                self.log_history.append(command)
                self.log_history.append(response)
                log_file = open(log_filename, "a")
                log_file.write(f"@CMD: {command}\n@Action: {self.action_set[action]}\n@RESP: {response}\n\n")
                log_file.close()

                # Send response
                self.channel.sendall(f'{response} ')

            except Exception as e:
                print("Channel closed:", e)
                self.channel.close()
                self.event.set()
                return

        self.channel.close()
        self.event.set()


def handleConnection(client, llm_model):
    transport = paramiko.Transport(client)
    transport.add_server_key(HOST_KEY)

    server_handler = SSHServerHandler(llm_model)
    transport.start_server(server=server_handler)            

    channel = transport.accept()

    if channel is None:
        transport.close()
        return
                         
    server_handler.channel = channel
    server_handler.handle_shell()

def start_ssh_server(llm_model):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', SSH_PORT))
        server_socket.listen(100)
        print('Server started...')

        while(True):
            try:
                client_socket, client_addr = server_socket.accept()
                print(f'New Connection: {client_addr}')
                threading.Thread(target=handleConnection, args=(client_socket,llm_model,)).start()
            except Exception as e:
                print("ERROR: Client handling")
                print(e)

    except Exception as e:
        print("ERROR: Failed to create socket")
        print(e)
        sys.exit(1)
