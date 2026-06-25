import socket
import sys
import threading
import paramiko
from datetime import datetime
import logging
import torch
import os
import time
from src.rl.dqn import DQN
import numpy as np
from src.shared import setting
from src.shared.prompts import PromptService
from src.shared.paths import (
    CHECKPOINTS_OUTPUT_DIR,
    HONEYPOT_LOGS_DIR,
    RUNTIME_OUTPUT_DIR,
    ensure_runtime_directories,
)

logger = logging.getLogger(__name__)

ensure_runtime_directories()
_server_key_path = RUNTIME_OUTPUT_DIR / "server.key"

# Generate SSH host key if it doesn't exist
def _generate_ssh_key(key_path):
    """Generate SSH RSA key if it doesn't exist"""
    if not os.path.exists(key_path):
        logger.info("SSH host key not found; generating %s", key_path)
        try:
            key = paramiko.RSAKey.generate(2048)
            key.write_private_key_file(str(key_path))
            logger.info("SSH host key generated at %s", key_path)
        except Exception:
            logger.exception("Failed to generate SSH host key at %s", key_path)
            raise

def _load_host_key():
    """Generate and load the SSH host key when the server starts."""
    _generate_ssh_key(_server_key_path)
    try:
        return paramiko.RSAKey(filename=str(_server_key_path))
    except Exception:
        logger.exception("Failed to load SSH host key from %s", _server_key_path)
        raise

SSH_PORT = 2222  # Use non-privileged port (22 requires root, 2222 doesn't)

# Log the user:password combinations to files
LOGFILE = HONEYPOT_LOGS_DIR / "auth.log"
LOGFILE_LOCK = threading.Lock()

N_STATES = 203

# 建立 DQN

dqn = None

# Mode variable (can be set via set_mode function)
_mode = 'train'  # Default to train mode

def get_model_path():
    """Get model path based on system and action"""
    model_file = None
    if setting.system == 'linux' and setting.action == 'Engage':
        model_file = 'model/02-07-04/model_02-07-04_episode_650'
    elif setting.system == 'linux' and setting.action == 'ABSI':
        model_file = 'model/02-17-18/model_02-17-18_episode_468'
    elif setting.system == 'windows' and setting.action == 'Engage':
        model_file = 'model/04-21-14/model_04-21-14_episode_847'
    elif setting.system == 'windows' and setting.action == 'ABSI':
        model_file = 'model/04-18-17/model_04-18-17_episode_722'
    
    if model_file:
        return os.path.join(CHECKPOINTS_OUTPUT_DIR, model_file)
    return None

def set_mode(mode):
    """Set the mode (train or test) and load model if needed"""
    global _mode, dqn
    _mode = mode
    setting.mode = mode

    if dqn is None:
        raise RuntimeError("DQN must be initialized before setting SSH server mode")
    
    if mode == 'test':
        # Test mode: Load model if exists
        model_path = get_model_path()
        if model_path and os.path.exists(model_path):
            logger.info("Test mode: loading model from %s", model_path)
            dqn.load(model_path)
            setting.epsilon = 0  # No exploration in test mode
            logger.info("Model loaded successfully; starting in test mode")
        else:
            logger.warning(
                "Model not found at %s; switching from test mode to train mode",
                model_path or "N/A",
            )
            _mode = 'train'
            setting.mode = 'train'
            setting.epsilon = 1
    else:
        # Train mode: Don't load model
        logger.info("Train mode: starting without a preloaded model")
        setting.epsilon = 1  # Full exploration in train mode

# Initialize mode (default: train, can be changed via set_mode before start_ssh_server is called)
# Don't call set_mode here - let it be called from main script


class SSHServerHandler(paramiko.ServerInterface):
    def __init__(self, llm_model):
        self.event = threading.Event()
        self.llm_model = llm_model
        self.log_history = []
        self.action_set = setting.action_set
        self.dqn = dqn  # Fix typo: dpn -> dqn
        self.prompt_service = PromptService(setting.system)

    def check_channel_request(self, kind, channelID): 
        return paramiko.OPEN_SUCCEEDED
    
    def check_channel_shell_request(self, channel): 
        logger.debug("SSH shell channel requested: %s", channel)
        self.channel = channel
        return True
    
    def check_channel_pty_request(self, c, t, w, h, p, ph, m): 
        return True    
    
    def check_auth_password(self, username, password):
        self.username = username
        self.password = password
        self.llm_model.add_system_prompt(self.username,self.password)
        # save login info to a file
        LOGFILE_LOCK.acquire()
        try:
            logfile_handle = LOGFILE.open("a", encoding="utf-8")
            logger.info("New SSH login attempt for user=%s", username)
            logfile_handle.write(username + ":" + password + "\n")
            logfile_handle.close()
        finally:
            LOGFILE_LOCK.release()

        return paramiko.AUTH_SUCCESSFUL
    
    def handle_shell(self):
        log_filename = HONEYPOT_LOGS_DIR / f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        time.sleep(1)
        response = self.llm_model.answer(self.action_set[0], '\n', self.log_history)
        self.channel.sendall(f'{response}')
        self.log_history.append('\n')
        self.log_history.append(response)
        while not self.channel.exit_status_ready():
            try:
                # Receive user input
                # self.channel.sendall(f'{self.username}@localhost:~/ $')
                buffer = ""
                while True:
                    # ✅ 一次讀 1 byte
                    char = self.channel.recv(1).decode("utf-8")

                    # 顯示回顯（回傳給 client 顯示打的字）
                    self.channel.send(char)

                    if char == '\r' or char == '\n':
                        break
                    else:
                        buffer += char

                command = buffer.strip()
                # command = self.channel.recv(1024).decode("utf-8").strip()
                
                logger.info("SSH command received: %s", command)
                if command == 'exit' or command == 'logout':
                    break
                start = datetime.now()
                # Detect state using generate()
                system_prompt = self.prompt_service.get_detector_state_prompt()
                message = ""
                if len(self.log_history) > 0:
                    for i, item in enumerate(self.log_history):
                        if i % 2 == 0:
                            message = message + "past_input: " + item + "\n"
                user_prompt = message + "current command: " + str(command) + "\n"
                
                # Use fine-tuned model for state detection if OpenAI
                model_override = None
                if self.llm_model.model_type == "openai":
                    model_override = "ft:gpt-4o-mini-2024-07-18:personal:detect-ttp-atomic-0924:AAqZyEOo"
                
                response = []
                while len(response) < 2:
                    resp = self.llm_model.generate(system_prompt, user_prompt, [], max_tokens=20, temperature=0.01, top_p=0.8, model_override=model_override)
                    response = resp.split(' ')
                    if len(response) < 2:
                        time.sleep(1)
                        continue
                
                # Translate IDs to indices
                tacticID = ['TA0001','TA0002', 'TA0003', 'TA0004', 'TA0005', 'TA0006', 'TA0007', 'TA0008', 'TA0009', 'TA0011', 'TA0010', 'TA0040']
                techniqueID = ['T1548', 'T1134', 'T1531', 'T1087', 'T1098', 'T1650', 'T1583', 'T1595', 'T1557', 'T1071', 'T1010', 'T1560', 'T1123', 'T1119', 'T1020', 'T1197', 'T1547', 'T1037', 'T1176', 'T1217', 'T1185', 'T1110', 'T1612', 'T1115', 'T1651', 'T1580', 'T1538', 'T1526', 'T1619', 'T1059', 'T1092', 'T1586', 'T1554', 'T1584', 'T1609', 'T1613', 'T1659', 'T1136', 'T1543', 'T1555', 'T1485', 'T1132', 'T1486', 'T1530', 'T1602', 'T1213', 'T1005', 'T1039', 'T1025', 'T1565', 'T1001', 'T1074', 'T1030', 'T1622', 'T1491', 'T1140', 'T1610', 'T1587', 'T1652', 'T1006', 'T1561', 'T1484', 'T1482', 'T1189', 'T1568', 'T1114', 'T1573', 'T1499', 'T1611', 'T1585', 'T1546', 'T1480', 'T1048', 'T1041', 'T1011', 'T1052', 'T1567', 'T1190', 'T1203', 'T1212', 'T1211', 'T1068', 'T1210', 'T1133', 'T1008', 'T1083', 'T1222', 'T1657', 'T1495', 'T1187', 'T1606', 'T1592', 'T1589', 'T1590', 'T1591', 'T1615', 'T1200', 'T1564', 'T1665', 'T1574', 'T1562', 'T1656', 'T1525', 'T1070', 'T1202', 'T1105', 'T1490', 'T1056', 'T1559', 'T1534', 'T1570', 'T1654', 'T1036', 'T1556', 'T1578', 'T1112', 'T1601', 'T1111', 'T1621', 'T1104', 'T1106', 'T1599', 'T1498', 'T1046', 'T1135', 'T1040', 'T1095', 'T1571', 'T1027', 'T1588', 'T1137', 'T1003', 'T1201', 'T1120', 'T1069', 'T1566', 'T1598', 'T1647', 'T1653', 'T1542', 'T1057', 'T1055', 'T1572', 'T1090', 'T1012', 'T1620', 'T1219', 'T1563', 'T1021', 'T1018', 'T1091', 'T1496', 'T1207', 'T1014', 'T1053', 'T1029', 'T1113', 'T1597', 'T1596', 'T1593', 'T1594', 'T1505', 'T1648', 'T1489', 'T1129', 'T1072', 'T1518', 'T1608', 'T1528', 'T1649', 'T1558', 'T1539', 'T1553', 'T1195', 'T1218', 'T1082', 'T1614', 'T1016', 'T1049', 'T1033', 'T1216', 'T1007', 'T1569', 'T1529', 'T1124', 'T1080', 'T1221', 'T1205', 'T1537', 'T1127', 'T1199', 'T1552', 'T1535', 'T1550', 'T1204', 'T1078', 'T1125', 'T1497', 'T1600', 'T1102', 'T1047', 'T1220']
                
                tactic = response[0]
                technique = response[1]
                if len(technique) > 5:
                    technique = technique[:5]
                
                tactic_id = tacticID.index(tactic) if tactic in tacticID else 1
                technique_id = techniqueID.index(technique) if technique in techniqueID else 1
                
                log_file = log_filename.open("a", encoding="utf-8")
                log_file.write(f"Detection Time: {datetime.now()- start}\n")
                log_file.close()
                state = np.zeros(N_STATES)
                state[technique_id-1] = 1

                action = dqn.choose_action(state)
                logger.info("Honeypot action selected: %s", self.action_set[action])
                # Produce output with LLM
                start = datetime.now()
                response = self.llm_model.answer(self.action_set[action], command, self.log_history)
                log_file = log_filename.open("a", encoding="utf-8")
                log_file.write(f"Generate Response Time: {datetime.now()- start}\n")
                log_file.close()
                logger.debug("Honeypot response: %s", response)
                
                # Save the logs
                self.log_history.append(command)
                self.log_history.append(response)
                log_file = log_filename.open("a", encoding="utf-8")
                log_file.write(f"@CMD: {command}\n@Action: {self.action_set[action]}\n@RESP: {response}\n\n")
                log_file.close()
                response2 = response.split('\n')
                for resp in response2:
                    resp.replace('\n','')
                    self.channel.sendall(f'\r\n{resp}')
                # Send response
                

            except Exception:
                logger.exception("SSH channel closed unexpectedly")
                self.channel.close()
                self.event.set()
                return

        self.channel.close()
        self.event.set()


def handle_connection(client, llm_model, host_key):
    transport = paramiko.Transport(client)
    transport.add_server_key(host_key)

    server_handler = SSHServerHandler(llm_model)
    transport.start_server(server=server_handler)            

    channel = transport.accept()

    if channel is None:
        transport.close()
        return
                         
    server_handler.channel = channel
    server_handler.handle_shell()

def start_ssh_server(llm_model, port=None, dqn_instance=None):
    """
    Start SSH server.
    
    Args:
        llm_model: LLM service instance
        port: SSH port number (default: SSH_PORT, which is 2222)
        dqn_instance: DQN instance to use (if None, uses global dqn)
    """
    if port is None:
        port = SSH_PORT

    host_key = _load_host_key()
    
    # Use the provided DQN instance or initialize one lazily.
    global dqn
    if dqn_instance is not None:
        dqn = dqn_instance
        logger.info("Using provided DQN instance (mode=%s)", setting.mode)
    elif dqn is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        n_actions = len(setting.action_set)
        logger.info("Initializing SSH honeypot DQN on %s", device)
        dqn = DQN(device, N_STATES, n_actions)
    
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', port))
        server_socket.listen(100)
        logger.info("SSH server started on port %d", port)
        
        while(True):
            try:
                client_socket, client_addr = server_socket.accept()
                logger.info("New SSH connection from %s", client_addr)
                threading.Thread(
                    target=handle_connection,
                    args=(client_socket, llm_model, host_key),
                    daemon=True,
                ).start()
            except Exception:
                logger.exception("Failed while handling SSH client")

    except Exception:
        logger.exception("Failed to create SSH server socket")
        sys.exit(1)
