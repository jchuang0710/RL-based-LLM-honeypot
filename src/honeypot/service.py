import gymnasium as gym
from gymnasium import spaces
import numpy as np
from datetime import datetime
import logging
import time
from src.shared import setting
from src.attacker.lifecycle import get_command, technique_exist
from src.shared.prompts import PromptService
from src.shared.paths import HONEYPOT_LOGS_DIR, ensure_runtime_directories
from src.shared.mitre import tactic_index, technique_index

logger = logging.getLogger(__name__)


class HoneypotService:
    """
    Honeypot service - handles command processing and response generation using RL.
    This represents the honeypot's perspective in the interaction.
    """
    
    def __init__(self, llm, rl_agent, action_set):
        """
        Initialize honeypot service.
        
        Args:
            llm: LLM service instance for generating responses
            rl_agent: RL agent (DQN/DDQN) for action selection
            action_set: List of available actions
        """
        self.llm = llm
        self.rl_agent = rl_agent
        self.action_set = action_set
        self.history = []
        self.n_states = 203  # Observation space size

    def process_command(self, command, state):
        """
        Process incoming command and generate response using RL agent.
        
        Args:
            command: Command from attacker
            state: Current state (technique vector)
        
        Returns:
            tuple: (response, next_state, reward, done, info)
        """
        # Choose action using RL agent
        action_idx = self.rl_agent.choose_action(state)
        action = self.action_set[action_idx]
        
        # Generate response using LLM
        response = self.llm.answer(action, command, self.history)
        
        # Update history
        self.history.append(command)
        self.history.append(response)
        
        # Detect next state (technique)
        tactic, technique = self._detect_state(action, command, self.history)
        
        # Build next state vector
        next_state = np.zeros(self.n_states)
        next_state[technique] = 1
        
        # Calculate reward (tactic depth)
        reward = tactic + 1
        
        # Check if honeypot is detected
        done = self._detect_honeypot(self.history)
        
        info = {
            'action': action,
            'action_idx': action_idx,
            'tactic': tactic,
            'technique': technique
        }
        
        return response, next_state, reward, done, info

    def reset(self):
        """Reset honeypot state"""
        self.history = []

    def add_interaction(self, command, response):
        """Add command-response pair to history"""
        self.history.append(command)
        self.history.append(response)

    def get_history(self):
        """Get interaction history"""
        return self.history.copy()


class HoneypotEnv(gym.Env):
    """
    Gym environment wrapper for honeypot training.
    Combines HoneypotService and AttackerService for RL training.
    """
    
    def __init__(self, llm, action_space, date):
        super(HoneypotEnv, self).__init__()
        self.action_space = spaces.Discrete(action_space)
        self.observation_space = spaces.Box(low=0, high=1, shape=(203,), dtype=np.float32)
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = []
        self.max_tactic = 1
        self.history = []
        self.date = date
        self.next_technique = ''
        self.llm = llm
        self.unknown_technique = 0
        ensure_runtime_directories()
        
        # Known techniques
        if setting.system == 'linux':
            self.known_technique = ['T1001.002', 'T1003.007', 'T1003.008', 'T1005', 'T1007', 'T1014', 'T1016.001', 'T1016', 'T1018', 'T1021.004', 'T1027.001', 'T1027.002', 'T1027.004', 'T1027', 'T1030', 'T1033', 'T1036.003', 'T1036.004', 'T1036.005', 'T1036.006', 'T1037.004', 'T1040', 'T1046', 'T1048.002', 'T1048.003', 'T1048', 'T1049', 'T1053.002', 'T1053.003', 'T1053.006', 'T1056.001', 'T1057', 'T1059.004', 'T1059.006', 'T1069.001', 'T1069.002', 'T1070.002', 'T1070.003', 'T1070.004', 'T1070.006', 'T1070.008', 'T1071.001', 'T1074.001', 'T1078.003', 'T1082', 'T1083', 'T1087.001', 'T1087.002', 'T1090.001', 'T1090.003', 'T1098.004', 'T1105', 'T1110.001', 'T1110.004', 'T1113', 'T1115', 'T1124', 'T1132.001', 'T1135', 'T1136.001', 'T1136.002', 'T1140 T1201', 'T1217', 'T1222.002', 'T1485', 'T1486', 'T1489', 'T1496', 'T1497.001', 'T1497.003', 'T1518.001', 'T1529', 'T1531', 'T1543.002', 'T1546.004', 'T1546.005', 'T1547.006', 'T1548.001', 'T1548.003', 'T1552.001', 'T1552.003', 'T1552.004', 'T1552.007', 'T1552', 'T1553.004', 'T1555.003', 'T1556.003', 'T1560.001', 'T1560.002', 'T1562.001', 'T1562.003', 'T1562.004', 'T1562.006', 'T1562.008', 'T1562.010', 'T1562.012', 'T1562', 'T1564.001', 'T1569.002', 'T1571', 'T1574.006', 'T1580', 'T1614.001', 'T1614']
        else:
            self.known_technique = ['T1652', 'T1037.001', 'T1136.002', 'T1486', 'T1137', 'T1553.003', 'T1187', 'T1010', 'T1574.011', 'T1218.005', 'T1069.002', 'T1119', 'T1110.002', 'T1201', 'T1036.003', 'T1087.002', 'T1091', 'T1018', 'T1220', 'T1546.008', 'T1557.001', 'T1572', 'T1055.012', 'T1095', 'T1110.004', 'T1040', 'T1003.003', 'T1055.004', 'T1546.011', 'T1222.001', 'T1127.001', 'T1574.002', 'T1027.007', 'T1505.005', 'T1560', 'T1543.003', 'T1072', 'T1053.002', 'T1059.003', 'T1078.003', 'T1090.001', 'T1558.002', 'T1134.004', 'T1114.001', 'T1547.012', 'T1120', 'T1055.011', 'T1547.009', 'T1547.002', 'T1134.001', 'T1090.003', 'T1558.001', 'T1003.004', 'T1112', 'T1574.001', 'T1020', 'T1564', 'T1055.015', 'T1007', 'T1137.004', 'T1222', 'T1574.012', 'T1560.001', 'T1071', 'T1016.001', 'T1059.005', 'T1218.004', 'T1137.006', 'T1562.002', 'T1070.003', 'T1033', 'T1567.003', 'T1573', 'T1055.001', 'T1484.001', 'T1012', 'T1195', 'T1001.002', 'T1489', 'T1070', 'T1071.001', 'T1547.001', 'T1556.002', 'T1567.002', 'T1003.006', 'T1529', 'T1218.011', 'T1005', 'T1106', 'T1482', 'T1552.002', 'T1654', 'T1197', 'T1016', 'T1127', 'T1123', 'T1218.009', 'T1542.001', 'T1559', 'T1563.002', 'T1539', 'T1622', 'T1552.001', 'T1218.003', 'T1497.001', 'T1217', 'T1491.001', 'T1110.003', 'T1547', 'T1574.008', 'T1574.009', 'T1059', 'T1069.001', 'T1546.013', 'T1615', 'T1137.001', 'T1555.003', 'T1559.002', 'T1553.006', 'T1564.003', 'T1070.005', 'T1546.009', 'T1649', 'T1048.002', 'T1569.002', 'T1562.004', 'T1505.003', 'T1027.006', 'T1547.015', 'T1550.002', 'T1055', 'T1553.005', 'T1614', 'T1087.001', 'T1219', 'T1547.003', 'T1553.004', 'T1592.001', 'T1132.001', 'T1113', 'T1027', 'T1057', 'T1218.002', 'T1555.004', 'T1027.004', 'T1485', 'T1564.002', 'T1571', 'T1218.008', 'T1562.001', 'T1036.005', 'T1546.015', 'T1021.003', 'T1082', 'T1030', 'T1055.002', 'T1176', 'T1124', 'T1056.001', 'T1137.002', 'T1552.006', 'T1550.003', 'T1555', 'T1021.002', 'T1083', 'T1546.001', 'T1021.001', 'T1202', 'T1049', 'T1048', 'T1566.001', 'T1216', 'T1564.004', 'T1078.001', 'T1070.001', 'T1136.001', 'T1216.001', 'T1548.002', 'T1204.003', 'T1125', 'T1046', 'T1021.006', 'T1059.007', 'T1620', 'T1614.001', 'T1003.002', 'T1221', 'T1546.010', 'T1218', 'T1039', 'T1547.004', 'T1558.004', 'T1547.008', 'T1134.002', 'T1558.003', 'T1041', 'T1003.001', 'T1564.001', 'T1505.004', 'T1547.006', 'T1129', 'T1218.007', 'T1562', 'T1546', 'T1070.008', 'T1531', 'T1552', 'T1070.006', 'T1006', 'T1490', 'T1546.007', 'T1570', 'T1048.003', 'T1552.004', 'T1135', 'T1003.005', 'T1110.001', 'T1204.002', 'T1207', 'T1505.002', 'T1546.002', 'T1218.001', 'T1562.003', 'T1134.005', 'T1036', 'T1056.004', 'T1016.002', 'T1518']

    def reset(self, lifecycle_command=None, seed=None, options=None):
        # Gymnasium API: reset() should return (observation, info)
        if lifecycle_command is None:
            lifecycle_command = []
        self.state = np.zeros(self.observation_space.shape[0])
        self.state[0] = 1
        self.command_buffer = lifecycle_command
        self.max_tactic = 1
        self.history = []
        self.unknown_technique = 0
        info = {}  # Optional info dict for gymnasium
        return self.state, info

    def step_llm(self, action):
        """Step function for RL training - combines honeypot and attacker logic"""
        reward = 0
        done = False

        # Honeypot: Generate response
        start = datetime.now()
        system_response = self.llm.answer(action, self.command_buffer[0], self.history)
        try:
            self.log_history(action, self.command_buffer[0], system_response)
        except OSError:
            logger.exception("Failed to write honeypot interaction history")
        self.history.append(action + self.command_buffer[0])
        self.history.append(system_response)
        del self.command_buffer[0]
 
        logger.debug("Generated honeypot response in %s", datetime.now() - start)
        self.next_state = np.zeros(self.observation_space.shape[0])
        start = datetime.now()
        
        # Attacker: Detect honeypot
        if self._detect_honeypot(self.history):
            terminated = True
            truncated = False
            self.next_state[-1] = 1
            logger.info("Honeypot detected by attacker; next_technique=%s", self.next_technique)
            return self.next_state, -5, terminated, truncated, {'technique':self.next_technique}
        
        # Attacker: Generate next attack technique if command buffer is empty
        if self.command_buffer == []:
            self.next_technique = ''
            while not technique_exist(self.next_technique):
                self.next_technique = self._get_next_attack_technique(self.history)
            self.command_buffer = get_command(self.next_technique)
            logger.info("Selected next attack technique: %s", self.next_technique)
        
            if self.next_technique not in self.known_technique:
                self.unknown_technique = self.unknown_technique + 1
        
        logger.debug("Detected state or selected command in %s", datetime.now() - start)
        start = datetime.now()
        
        # Attacker: Detect next state
        tactic, technique = self._detect_state(action, self.command_buffer[0], self.history)
        with (HONEYPOT_LOGS_DIR / f"interaction_{self.date}.log").open("a", encoding="utf-8") as f:
            f.write('tactic:' + str(tactic) + "\n")
            f.write('technique:' + str(technique) + "\n")
            f.write("\n\n")
        logger.debug("Analyzed attacker command in %s", datetime.now() - start)
        logger.info("Detected tactic=%s technique=%s", tactic, technique)
        self.next_state = np.zeros(self.observation_space.shape[0])
        self.next_state[technique] = 1

        reward = tactic + 1
        if self.max_tactic < tactic + 1:
            self.max_tactic = tactic + 1

        # Gymnasium API: step() returns (observation, reward, terminated, truncated, info)
        terminated = done
        truncated = False
        return self.next_state, reward, terminated, truncated, {}

    def log_history(self, action, command, response):
        with (HONEYPOT_LOGS_DIR / f"interaction_{self.date}.log").open("a", encoding="utf-8") as f:
            f.write("action:" + action + "\n")
            f.write("command:" + command + "\n")
            f.write("response:" + response + "\n")

    def _detect_honeypot(self, log_history):
        """Detect if system is honeypot"""
        system_prompt = self.prompt_service.get_detector_prompt()
        message = ""
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message = message + "input: " + item + "\n"
                else:
                    message = message + "output: " + item + "\n"
        
        response = self.llm.generate(system_prompt, message, [], max_tokens=5, temperature=0.01, top_p=0.8)
        return response.strip().lower() == "yes"
    
    def _detect_state(self, action, query, log_history):
        """Detect next MITRE tactic and technique"""
        system_prompt = self.prompt_service.get_detector_state_prompt()
        message = ""
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message = message + "past_input: " + item + "\n"
        
        user_prompt = message + "current command: " + str(query) + "\n"
        
        # Use fine-tuned model for state detection if OpenAI
        model_override = None
        if self.llm.model_type == "openai":
            model_override = "ft:gpt-4o-mini-2024-07-18:personal:detect-ttp-atomic-0924:AAqZyEOo"
        
        response = []
        while len(response) < 2:
            resp = self.llm.generate(system_prompt, user_prompt, [], max_tokens=20, temperature=0.01, top_p=0.8, model_override=model_override)
            response = resp.split(' ')
            if len(response) < 2:
                time.sleep(1)
                continue
        
        return self._translate_tactic_id(response[0]), self._translate_technique_id(response[1])
    
    def _get_next_attack_technique(self, log_history):
        """Get next attack technique based on log history"""
        # Get technique list based on system
        if setting.system == 'linux':
            technique_list = "T1001.002 T1003.007 T1003.008 T1005 T1007 T1014 T1016.001 T1016 T1018 T1021.004 T1027.001 T1027.002 T1027.004 T1027 T1030 T1033 T1036.003 T1036.004 T1036.005 T1036.006 T1037.004 T1040 T1046 T1048.002 T1048.003 T1048 T1049 T1053.002 T1053.003 T1053.006 T1056.001 T1057 T1059.004 T1059.006 T1069.001 T1069.002 T1070.002 T1070.003 T1070.004 T1070.006 T1070.008 T1071.001 T1074.001 T1078.003 T1082 T1083 T1087.001 T1087.002 T1090.001 T1090.003 T1098.004 T1105 T1110.001 T1110.004 T1113 T1115 T1124 T1132.001 T1135 T1136.001 T1136.002 T1140 T1201 T1217 T1222.002 T1485 T1486 T1489 T1496 T1497.001 T1497.003 T1518.001 T1529 T1531 T1543.002 T1546.004 T1546.005 T1547.006 T1548.001 T1548.003 T1552.001 T1552.003 T1552.004 T1552.007 T1552 T1553.004 T1555.003 T1556.003 T1560.001 T1560.002 T1562.001 T1562.003 T1562.004 T1562.006 T1562.008 T1562.010 T1562.012 T1562 T1564.001 T1569.002 T1571 T1574.006 T1580 T1614.001 T1614"
        else:  # windows
            technique_list = "T1652 T1037.001 T1136.002 T1486 T1137 T1553.003 T1187 T1010 T1574.011 T1218.005 T1069.002 T1119 T1110.002 T1201 T1036.003 T1087.002 T1091 T1018 T1220 T1546.008 T1557.001 T1572 T1055.012 T1095 T1110.004 T1040 T1003.003 T1055.004 T1546.011 T1222.001 T1127.001 T1574.002 T1027.007 T1505.005 T1560 T1543.003 T1072 T1053.002 T1059.003 T1078.003 T1090.001 T1558.002 T1134.004 T1114.001 T1547.012 T1120 T1055.011 T1547.009 T1547.002 T1134.001 T1090.003 T1558.001 T1003.004 T1112 T1574.001 T1020 T1564 T1055.015 T1007 T1137.004 T1222 T1574.012 T1560.001 T1071 T1016.001 T1059.005 T1218.004 T1137.006 T1562.002 T1070.003 T1033 T1567.003 T1573 T1055.001 T1484.001 T1012 T1195 T1001.002 T1489 T1070 T1071.001 T1547.001 T1556.002 T1567.002 T1003.006 T1529 T1218.011 T1005 T1106 T1482 T1552.002 T1654 T1197 T1016 T1127 T1123 T1218.009 T1542.001 T1559 T1563.002 T1539 T1622 T1552.001 T1218.003 T1497.001 T1217 T1491.001 T1110.003 T1547 T1574.008 T1574.009 T1059 T1069.001 T1546.013 T1615 T1137.001 T1555.003 T1559.002 T1553.006 T1564.003 T1070.005 T1546.009 T1649 T1048.002 T1569.002 T1562.004 T1505.003 T1027.006 T1547.015 T1550.002 T1055 T1553.005 T1614 T1087.001 T1219 T1547.003 T1553.004 T1592.001 T1132.001 T1113 T1027 T1057 T1218.002 T1555.004 T1027.004 T1485 T1564.002 T1571 T1218.008 T1562.001 T1036.005 T1546.015 T1021.003 T1082 T1030 T1055.002 T1176 T1124 T1056.001 T1137.002 T1552.006 T1550.003 T1555 T1021.002 T1083 T1546.001 T1021.001 T1202 T1049 T1048 T1566.001 T1216 T1564.004 T1078.001 T1070.001 T1136.001 T1216.001 T1548.002 T1204.003 T1125 T1046 T1021.006 T1059.007 T1620 T1614.001 T1003.002 T1221 T1546.010 T1218 T1039 T1547.004 T1558.004 T1547.008 T1134.002 T1558.003 T1041 T1003.001 T1564.001 T1505.004 T1547.006 T1129 T1218.007 T1562 T1546 T1070.008 T1531 T1552 T1070.006 T1006 T1490 T1546.007 T1570 T1048.003 T1552.004 T1135 T1003.005 T1110.001 T1204.002 T1207 T1505.002 T1546.002 T1218.001 T1562.003 T1134.005 T1036 T1056.004 T1016.002 T1518"
        
        system_prompt = self.prompt_service.get_attacker_prompt(technique_list)
        message = ""
        if len(log_history) > 0:
            for i, item in enumerate(log_history):
                if i % 2 == 0:
                    message = message + "input: " + item + "\n"
                else:
                    message = message + "output: " + item + "\n"
        
        return self.llm.generate(system_prompt, message, [], max_tokens=10, temperature=0.01, top_p=0.8)
    
    def _translate_tactic_id(self, tactic):
        """Translate MITRE tactic ID to index"""
        return tactic_index(tactic)
    
    def _translate_technique_id(self, technique):
        """Translate MITRE technique ID to index"""
        return technique_index(technique)

    def close(self):
        pass
