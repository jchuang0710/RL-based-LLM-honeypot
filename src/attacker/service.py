import logging
import socket
import time
import re
from pathlib import Path
from src.attacker.lifecycle import get_command, get_technique_command, technique_exist
from src.shared.prompts import PromptService
from src.shared import setting
from src.shared.paths import ATTACKER_LOGS_DIR, ensure_runtime_directories
from src.shared.mitre import (
    parse_state_response,
    tactic_index,
    technique_index,
)
import paramiko

logger = logging.getLogger(__name__)


class AttackerService:
    """
    Attacker service - handles command execution, state detection, and attack technique generation.
    This represents the attacker's perspective in the honeypot interaction.
    """
    
    def __init__(self, llm):
        """
        Initialize attacker service.
        
        Args:
            llm: LLM service instance for detection and technique generation
        """
        self.llm = llm
        self.prompt_service = PromptService(setting.system)
        self.history = []
        self.command_buffer = []
        self.unknown_technique = 0
        ensure_runtime_directories()
        
        # Known techniques based on system
        if setting.system == 'linux':
            self.known_technique = ['T1001.002', 'T1003.007', 'T1003.008', 'T1005', 'T1007', 'T1014', 'T1016.001', 'T1016', 'T1018', 'T1021.004', 'T1027.001', 'T1027.002', 'T1027.004', 'T1027', 'T1030', 'T1033', 'T1036.003', 'T1036.004', 'T1036.005', 'T1036.006', 'T1037.004', 'T1040', 'T1046', 'T1048.002', 'T1048.003', 'T1048', 'T1049', 'T1053.002', 'T1053.003', 'T1053.006', 'T1056.001', 'T1057', 'T1059.004', 'T1059.006', 'T1069.001', 'T1069.002', 'T1070.002', 'T1070.003', 'T1070.004', 'T1070.006', 'T1070.008', 'T1071.001', 'T1074.001', 'T1078.003', 'T1082', 'T1083', 'T1087.001', 'T1087.002', 'T1090.001', 'T1090.003', 'T1098.004', 'T1105', 'T1110.001', 'T1110.004', 'T1113', 'T1115', 'T1124', 'T1132.001', 'T1135', 'T1136.001', 'T1136.002', 'T1140 T1201', 'T1217', 'T1222.002', 'T1485', 'T1486', 'T1489', 'T1496', 'T1497.001', 'T1497.003', 'T1518.001', 'T1529', 'T1531', 'T1543.002', 'T1546.004', 'T1546.005', 'T1547.006', 'T1548.001', 'T1548.003', 'T1552.001', 'T1552.003', 'T1552.004', 'T1552.007', 'T1552', 'T1553.004', 'T1555.003', 'T1556.003', 'T1560.001', 'T1560.002', 'T1562.001', 'T1562.003', 'T1562.004', 'T1562.006', 'T1562.008', 'T1562.010', 'T1562.012', 'T1562', 'T1564.001', 'T1569.002', 'T1571', 'T1574.006', 'T1580', 'T1614.001', 'T1614']
        else:  # windows
            self.known_technique = ['T1652', 'T1037.001', 'T1136.002', 'T1486', 'T1137', 'T1553.003', 'T1187', 'T1010', 'T1574.011', 'T1218.005', 'T1069.002', 'T1119', 'T1110.002', 'T1201', 'T1036.003', 'T1087.002', 'T1091', 'T1018', 'T1220', 'T1546.008', 'T1557.001', 'T1572', 'T1055.012', 'T1095', 'T1110.004', 'T1040', 'T1003.003', 'T1055.004', 'T1546.011', 'T1222.001', 'T1127.001', 'T1574.002', 'T1027.007', 'T1505.005', 'T1560', 'T1543.003', 'T1072', 'T1053.002', 'T1059.003', 'T1078.003', 'T1090.001', 'T1558.002', 'T1134.004', 'T1114.001', 'T1547.012', 'T1120', 'T1055.011', 'T1547.009', 'T1547.002', 'T1134.001', 'T1090.003', 'T1558.001', 'T1003.004', 'T1112', 'T1574.001', 'T1020', 'T1564', 'T1055.015', 'T1007', 'T1137.004', 'T1222', 'T1574.012', 'T1560.001', 'T1071', 'T1016.001', 'T1059.005', 'T1218.004', 'T1137.006', 'T1562.002', 'T1070.003', 'T1033', 'T1567.003', 'T1573', 'T1055.001', 'T1484.001', 'T1012', 'T1195', 'T1001.002', 'T1489', 'T1070', 'T1071.001', 'T1547.001', 'T1556.002', 'T1567.002', 'T1003.006', 'T1529', 'T1218.011', 'T1005', 'T1106', 'T1482', 'T1552.002', 'T1654', 'T1197', 'T1016', 'T1127', 'T1123', 'T1218.009', 'T1542.001', 'T1559', 'T1563.002', 'T1539', 'T1622', 'T1552.001', 'T1218.003', 'T1497.001', 'T1217', 'T1491.001', 'T1110.003', 'T1547', 'T1574.008', 'T1574.009', 'T1059', 'T1069.001', 'T1546.013', 'T1615', 'T1137.001', 'T1555.003', 'T1559.002', 'T1553.006', 'T1564.003', 'T1070.005', 'T1546.009', 'T1649', 'T1048.002', 'T1569.002', 'T1562.004', 'T1505.003', 'T1027.006', 'T1547.015', 'T1550.002', 'T1055', 'T1553.005', 'T1614', 'T1087.001', 'T1219', 'T1547.003', 'T1553.004', 'T1592.001', 'T1132.001', 'T1113', 'T1027', 'T1057', 'T1218.002', 'T1555.004', 'T1027.004', 'T1485', 'T1564.002', 'T1571', 'T1218.008', 'T1562.001', 'T1036.005', 'T1546.015', 'T1021.003', 'T1082', 'T1030', 'T1055.002', 'T1176', 'T1124', 'T1056.001', 'T1137.002', 'T1552.006', 'T1550.003', 'T1555', 'T1021.002', 'T1083', 'T1546.001', 'T1021.001', 'T1202', 'T1049', 'T1048', 'T1566.001', 'T1216', 'T1564.004', 'T1078.001', 'T1070.001', 'T1136.001', 'T1216.001', 'T1548.002', 'T1204.003', 'T1125', 'T1046', 'T1021.006', 'T1059.007', 'T1620', 'T1614.001', 'T1003.002', 'T1221', 'T1546.010', 'T1218', 'T1039', 'T1547.004', 'T1558.004', 'T1547.008', 'T1134.002', 'T1558.003', 'T1041', 'T1003.001', 'T1564.001', 'T1505.004', 'T1547.006', 'T1129', 'T1218.007', 'T1562', 'T1546', 'T1070.008', 'T1531', 'T1552', 'T1070.006', 'T1006', 'T1490', 'T1546.007', 'T1570', 'T1048.003', 'T1552.004', 'T1135', 'T1003.005', 'T1110.001', 'T1204.002', 'T1207', 'T1505.002', 'T1546.002', 'T1218.001', 'T1562.003', 'T1134.005', 'T1036', 'T1056.004', 'T1016.002', 'T1518']

    def reset(self, initial_commands=None):
        """Reset attacker state"""
        if initial_commands is None:
            initial_commands = ['whoami']
        self.command_buffer = initial_commands
        self.history = []
        self.unknown_technique = 0

    def execute_command(self, command):
        raise NotImplementedError("Use a transport-specific attacker service")

    def _translate_tactic_id(self, tactic):
        """Translate MITRE tactic ID to index"""
        return tactic_index(tactic)
    
    def _translate_technique_id(self, technique):
        """Translate MITRE technique ID to index"""
        return technique_index(technique)

    def get_next_attack_technique(self, log_history=None, technique_set=None):
        """
        Generate next attack technique based on interaction history.
        
        Args:
            log_history: Interaction history (if None, uses self.history)
            technique_set: Optional technique list (if None, uses system default)
        
        Returns:
            str: Next attack technique ID
        """
        history = log_history if log_history is not None else self.history
        
        # Get technique list based on system
        if technique_set is None:
            if setting.system == 'linux':
                technique_list = "T1001.002 T1003.007 T1003.008 T1005 T1007 T1014 T1016.001 T1016 T1018 T1021.004 T1027.001 T1027.002 T1027.004 T1027 T1030 T1033 T1036.003 T1036.004 T1036.005 T1036.006 T1037.004 T1040 T1046 T1048.002 T1048.003 T1048 T1049 T1053.002 T1053.003 T1053.006 T1056.001 T1057 T1059.004 T1059.006 T1069.001 T1069.002 T1070.002 T1070.003 T1070.004 T1070.006 T1070.008 T1071.001 T1074.001 T1078.003 T1082 T1083 T1087.001 T1087.002 T1090.001 T1090.003 T1098.004 T1105 T1110.001 T1110.004 T1113 T1115 T1124 T1132.001 T1135 T1136.001 T1136.002 T1140 T1201 T1217 T1222.002 T1485 T1486 T1489 T1496 T1497.001 T1497.003 T1518.001 T1529 T1531 T1543.002 T1546.004 T1546.005 T1547.006 T1548.001 T1548.003 T1552.001 T1552.003 T1552.004 T1552.007 T1552 T1553.004 T1555.003 T1556.003 T1560.001 T1560.002 T1562.001 T1562.003 T1562.004 T1562.006 T1562.008 T1562.010 T1562.012 T1562 T1564.001 T1569.002 T1571 T1574.006 T1580 T1614.001 T1614"
            else:  # windows
                technique_list = "T1652 T1037.001 T1136.002 T1486 T1137 T1553.003 T1187 T1010 T1574.011 T1218.005 T1069.002 T1119 T1110.002 T1201 T1036.003 T1087.002 T1091 T1018 T1220 T1546.008 T1557.001 T1572 T1055.012 T1095 T1110.004 T1040 T1003.003 T1055.004 T1546.011 T1222.001 T1127.001 T1574.002 T1027.007 T1505.005 T1560 T1543.003 T1072 T1053.002 T1059.003 T1078.003 T1090.001 T1558.002 T1134.004 T1114.001 T1547.012 T1120 T1055.011 T1547.009 T1547.002 T1134.001 T1090.003 T1558.001 T1003.004 T1112 T1574.001 T1020 T1564 T1055.015 T1007 T1137.004 T1222 T1574.012 T1560.001 T1071 T1016.001 T1059.005 T1218.004 T1137.006 T1562.002 T1070.003 T1033 T1567.003 T1573 T1055.001 T1484.001 T1012 T1195 T1001.002 T1489 T1070 T1071.001 T1547.001 T1556.002 T1567.002 T1003.006 T1529 T1218.011 T1005 T1106 T1482 T1552.002 T1654 T1197 T1016 T1127 T1123 T1218.009 T1542.001 T1559 T1563.002 T1539 T1622 T1552.001 T1218.003 T1497.001 T1217 T1491.001 T1110.003 T1547 T1574.008 T1574.009 T1059 T1069.001 T1546.013 T1615 T1137.001 T1555.003 T1559.002 T1553.006 T1564.003 T1070.005 T1546.009 T1649 T1048.002 T1569.002 T1562.004 T1505.003 T1027.006 T1547.015 T1550.002 T1055 T1553.005 T1614 T1087.001 T1219 T1547.003 T1553.004 T1592.001 T1132.001 T1113 T1027 T1057 T1218.002 T1555.004 T1027.004 T1485 T1564.002 T1571 T1218.008 T1562.001 T1036.005 T1546.015 T1021.003 T1082 T1030 T1055.002 T1176 T1124 T1056.001 T1137.002 T1552.006 T1550.003 T1555 T1021.002 T1083 T1546.001 T1021.001 T1202 T1049 T1048 T1566.001 T1216 T1564.004 T1078.001 T1070.001 T1136.001 T1216.001 T1548.002 T1204.003 T1125 T1046 T1021.006 T1059.007 T1620 T1614.001 T1003.002 T1221 T1546.010 T1218 T1039 T1547.004 T1558.004 T1547.008 T1134.002 T1558.003 T1041 T1003.001 T1564.001 T1505.004 T1547.006 T1129 T1218.007 T1562 T1546 T1070.008 T1531 T1552 T1070.006 T1006 T1490 T1546.007 T1570 T1048.003 T1552.004 T1135 T1003.005 T1110.001 T1204.002 T1207 T1505.002 T1546.002 T1218.001 T1562.003 T1134.005 T1036 T1056.004 T1016.002 T1518"
        else:
            if isinstance(technique_set, list):
                technique_list = ' '.join(technique_set)
            else:
                technique_list = technique_set
        
        # Format message from history
        system_prompt = self.prompt_service.get_attacker_prompt(technique_list)
        
        # Build user prompt: ask for next technique
        # The history will be passed separately as log_history, so we don't need to include it here
        # Make it very clear that we want ONLY the technique ID
        if len(history) > 0:
            user_prompt = "Based on the interaction history above, what is the next MITRE technique ID I should use? Reply with ONLY the technique ID (e.g., T1003.007 or T1001.002), no explanation, no other text."
        else:
            user_prompt = "What is the next MITRE technique ID I should use? Reply with ONLY the technique ID (e.g., T1003.007 or T1001.002), no explanation, no other text."
        
        # Call generate and process result
        # Pass history as log_history so it's properly formatted in the conversation
        next_technique = ''
        max_retries = 10  # Limit retries to avoid infinite loop
        retry_count = 0
        
        while not technique_exist(next_technique) and retry_count < max_retries:
            logger.debug(
                "Generating attack technique (attempt %d/%d)",
                retry_count + 1,
                max_retries,
            )
            raw_response = self.llm.generate(system_prompt, user_prompt, history, max_tokens=10, temperature=0.1, top_p=0.8)
            logger.debug("Attack technique raw response: %s", raw_response)
            # Clean and extract technique ID from response
            # Extract first valid technique pattern (e.g., T1001, T1001.002)
            # Ignore anything before T, match T followed by digits, optionally with .XXX
            match = re.search(r'T\d+(?:\.\d+)?', raw_response)
            if match:
                next_technique = match.group(0)
            else:
                # If no pattern found, try a more lenient pattern (T followed by alphanumeric)
                match = re.search(r'T[A-Z0-9]+(?:\.[A-Z0-9]+)?', raw_response)
                if match:
                    next_technique = match.group(0)
                else:
                    next_technique = ''
            
            logger.debug(
                "Attack technique response parsed: raw=%r extracted=%r",
                raw_response,
                next_technique,
            )
            retry_count += 1
        
        if not technique_exist(next_technique):
            logger.warning(
                "Failed to generate a valid technique after %d attempts; last=%r",
                max_retries,
                next_technique,
            )
            # Fallback: find a valid technique from known list that exists in technique_command
            technique_command = get_technique_command()
            fallback_found = False
            for tech in self.known_technique:
                if tech in technique_command and technique_command[tech] != []:
                    next_technique = tech
                    logger.warning("Using fallback technique: %s", next_technique)
                    fallback_found = True
                    break
            
            if not fallback_found:
                # Last resort: find any valid technique from technique_command
                for tech_id in technique_command.keys():
                    if technique_command[tech_id] != []:
                        next_technique = tech_id
                        logger.error("Using emergency fallback technique: %s", next_technique)
                        break
                else:
                    # If still no valid technique found, raise an error with helpful message
                    available_techniques = list(technique_command.keys())[:10]  # Show first 10 for debugging
                    raise ValueError(
                        f"No valid technique found in technique_command. "
                        f"Available techniques (first 10): {available_techniques}. "
                        f"Please check if atomic-red-team YAML files are properly loaded."
                    )
        
        if next_technique not in self.known_technique:
            self.unknown_technique += 1
        
        return next_technique

    def get_commands_for_technique(self, technique):
        """
        Get commands for a specific MITRE technique using ART.
        
        Args:
            technique: MITRE technique ID
        
        Returns:
            list: List of commands
        """
        # Verify technique exists before calling get_command
        if not technique_exist(technique):
            technique_command = get_technique_command()
            available_techniques = list(technique_command.keys())[:20]  # Show first 20 for debugging
            raise KeyError(
                f"Technique '{technique}' not found in technique_command. "
                f"Available techniques (first 20): {available_techniques}"
            )
        return get_command(technique)

    def add_interaction(self, command, response):
        """Add command-response pair to history"""
        self.history.append(command)
        self.history.append(response)

    def detect_honeypot(self, history=None):
        """Use the configured LLM to classify the current target."""
        interaction_history = history if history is not None else self.history
        message = self._format_history(interaction_history)
        response = self.llm.generate(
            self.prompt_service.get_detector_prompt(),
            message,
            [],
            max_tokens=5,
            temperature=0.01,
            top_p=0.8,
        )
        return response.strip().lower().startswith("yes")

    def detect_state(self, command, history=None):
        """Detect the MITRE tactic and base technique for a command."""
        interaction_history = history if history is not None else self.history
        past_commands = "\n".join(
            f"past_input: {item}"
            for index, item in enumerate(interaction_history)
            if index % 2 == 0
        )
        user_prompt = f"{past_commands}\ncurrent command: {command}\n".lstrip()
        model_override = None
        if self.llm.model_type == "openai":
            model_override = (
                "ft:gpt-4o-mini-2024-07-18:personal:"
                "detect-ttp-atomic-0924:AAqZyEOo"
            )
        response = self.llm.generate(
            self.prompt_service.get_detector_state_prompt(),
            user_prompt,
            [],
            max_tokens=20,
            temperature=0.01,
            top_p=0.8,
            model_override=model_override,
        )
        tactic, technique = parse_state_response(response)
        return {
            "tactic": tactic,
            "technique": technique,
            "tactic_index": tactic_index(tactic),
            "technique_index": technique_index(technique),
        }

    @staticmethod
    def _format_history(history):
        lines = []
        for index, item in enumerate(history):
            label = "input" if index % 2 == 0 else "output"
            lines.append(f"{label}: {item}")
        return "\n".join(lines)

    def log_interaction(self, action, command, response, log_file=None):
        """Log interaction to file"""
        path = ATTACKER_LOGS_DIR / (log_file or "interactions.log")
        with path.open("a", encoding="utf-8") as f:
            f.write("action:" + action + "\n")
            f.write("command:" + command + "\n")
            f.write("response:" + response + "\n")


class AttackerSSHService(AttackerService):
    """
    Attacker service that uses SSH connection to execute commands.
    """
    
    def __init__(
        self,
        llm,
        hostname,
        port=22,
        username="root",
        password=None,
        key_filename=None,
        connect_timeout=10.0,
        command_timeout=15.0,
        idle_timeout=1.0,
        read_buffer_size=65535,
    ):
        super().__init__(llm)
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = str(Path(key_filename).expanduser()) if key_filename else None
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self.idle_timeout = idle_timeout
        self.read_buffer_size = read_buffer_size
        self.client = None
        self.shell = None
        self._connect()

    def _connect(self):
        """Connect to SSH server"""
        self.close()
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        logger.info(
            "Connecting to SSH target %s:%d as %s",
            self.hostname,
            self.port,
            self.username,
        )
        self.client.connect(
            self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
            key_filename=self.key_filename,
            timeout=self.connect_timeout,
            banner_timeout=self.connect_timeout,
            auth_timeout=self.connect_timeout,
            allow_agent=self.password is None and self.key_filename is None,
            look_for_keys=self.password is None and self.key_filename is None,
        )
        transport = self.client.get_transport()
        if transport is not None:
            transport.set_keepalive(30)
        self.shell = self.client.invoke_shell(width=160, height=48)
        banner = self._read_response(timeout=self.connect_timeout)
        if banner:
            logger.debug("SSH target banner: %s", banner)
        logger.info("Connected to SSH target %s:%d", self.hostname, self.port)

    def execute_command(self, command):
        """Execute command via SSH"""
        if not command.strip():
            return ""
        try:
            if self.shell is None or self.shell.closed:
                self._connect()
            self.shell.sendall(command.rstrip() + "\n")
            return self._read_response(timeout=self.command_timeout)
        except (EOFError, OSError, socket.error, paramiko.SSHException):
            logger.warning("SSH connection lost; reconnecting once", exc_info=True)
            self._connect()
            self.shell.sendall(command.rstrip() + "\n")
            return self._read_response(timeout=self.command_timeout)

    def _read_response(self, timeout):
        """Read until the channel stays idle or the overall timeout expires."""
        if self.shell is None:
            raise RuntimeError("SSH shell is not connected")

        chunks = []
        deadline = time.monotonic() + timeout
        last_data_at = None

        while time.monotonic() < deadline:
            if self.shell.recv_ready():
                data = self.shell.recv(self.read_buffer_size)
                if not data:
                    break
                chunks.append(data)
                last_data_at = time.monotonic()
                continue

            if self.shell.closed or self.shell.exit_status_ready():
                break
            if last_data_at is not None and time.monotonic() - last_data_at >= self.idle_timeout:
                break
            time.sleep(0.05)

        response = b"".join(chunks).decode("utf-8", errors="replace")
        return response.replace("\r\n", "\n").strip()

    def close(self):
        """Close SSH connection"""
        if self.shell:
            self.shell.close()
            self.shell = None
        if self.client:
            self.client.close()
            self.client = None

    def reconnect(self):
        """Start a fresh SSH session."""
        self._connect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
