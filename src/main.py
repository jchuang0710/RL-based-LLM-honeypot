"""
Unified Main - Runs both Honeypot and Attacker in the same process
This allows them to share the same LLM instance, saving GPU memory.

Usage:
    python -m src.main [--mode train|test] [--port PORT]
    
    --mode: 'train' for training mode, 'test' for test mode (default: 'train')
    --port: SSH server port (default: 2222)
"""
import argparse
import threading
import time
import logging

from src.honeypot.ssh_server import start_ssh_server
from src.attacker.service import AttackerSSHService
from src.shared import InitializationManager
from src.shared.logging import configure_logging

logger = logging.getLogger(__name__)


def run_honeypot_server(init_manager, port):
    """Run honeypot SSH server in a separate thread"""
    logger.info("Starting honeypot SSH server")
    # Pass DQN instance to use the shared one from initialization manager
    start_ssh_server(init_manager.llm_service, port=port, dqn_instance=init_manager.dqn)


def run_attacker(init_manager):
    """Run attacker logic"""
    logger.info("Starting attacker")
    
    # Get services from manager (will reuse shared LLM)
    llm = init_manager.llm_service
    prompt_service = init_manager.prompt_service
    
    attacker = AttackerSSHService(
        llm,
        hostname="127.0.0.1",
        port=init_manager.ssh_port,
        username="root",
        password="password",
    )
    
    logger.info("Attacker initialized; starting attack sequence")
    
    max_episodes = 200
    
    for episode in range(max_episodes):
        logger.info("Starting episode %d/%d", episode + 1, max_episodes)
        
        # Reset attacker state for each episode (start with whoami)
        attacker.reset(['whoami'])
        
        # Each episode has multiple steps
        step = 0
        max_steps_per_episode = 50  # Maximum steps per episode to prevent infinite loops
        
        while step < max_steps_per_episode:
            step += 1
            logger.debug("Episode %d step %d", episode + 1, step)
            
            # Get next command from buffer
            if not attacker.command_buffer:
                # Generate next attack technique
                logger.info("Generating next attack technique")
                next_technique = attacker.get_next_attack_technique()
                logger.info("Next attack technique: %s", next_technique)
                
                # Get commands for this technique
                attacker.command_buffer = attacker.get_commands_for_technique(next_technique)
                logger.info(
                    "Loaded %d commands for technique %s",
                    len(attacker.command_buffer),
                    next_technique,
                )
            
            # Execute command
            command = attacker.command_buffer.pop(0)
            logger.info("Executing attacker command: %s", command)
            
            response = attacker.execute_command(command)
            
            # Add to history
            attacker.add_interaction(command, response)
            
            # Detect if honeypot
            system_prompt = prompt_service.get_detector_prompt()
            message = ""
            if len(attacker.history) > 0:
                for i, item in enumerate(attacker.history):
                    if i % 2 == 0:
                        message = message + "input: " + item + "\n"
                    else:
                        message = message + "output: " + item + "\n"
            
            response_detect = attacker.llm.generate(system_prompt, message, [], max_tokens=5, temperature=0.01, top_p=0.8)
            is_honeypot = response_detect.strip().lower() == "yes"
            if is_honeypot:
                logger.warning("Honeypot detected; ending episode")
                break  # End current episode, continue to next episode
            
            # Detect current state
            system_prompt = prompt_service.get_detector_state_prompt()
            message = ""
            if len(attacker.history) > 0:
                for i, item in enumerate(attacker.history):
                    if i % 2 == 0:
                        message = message + "past_input: " + item + "\n"
            
            user_prompt = message + "current command: " + str(command) + "\n"
            
            # Use fine-tuned model for state detection if OpenAI
            model_override = None
            if attacker.llm.model_type == "openai":
                model_override = "ft:gpt-4o-mini-2024-07-18:personal:detect-ttp-atomic-0924:AAqZyEOo"
            
            response_state = []
            max_retries = 5
            retry_count = 0
            import re
            
            while len(response_state) < 2 and retry_count < max_retries:
                resp = attacker.llm.generate(system_prompt, user_prompt, [], max_tokens=20, temperature=0.01, top_p=0.8, model_override=model_override)
                logger.debug("State detection raw response: %r", resp)
                
                # Clean response: remove newlines, extra spaces
                resp_clean = resp.strip().replace('\n', ' ').replace('\r', ' ')
                
                # First, try to extract tactic and technique using regex (most reliable)
                # Look for TA#### pattern (tactic) and T#### pattern (technique)
                tactic_match = re.search(r'TA\d+', resp_clean)
                technique_match = re.search(r'T\d+', resp_clean)
                
                if tactic_match and technique_match:
                    # Found both, use them
                    tactic_id = tactic_match.group(0)
                    technique_id = technique_match.group(0)
                    # Make sure technique comes after tactic in the response
                    if resp_clean.find(tactic_id) < resp_clean.find(technique_id):
                        response_state = [tactic_id, technique_id]
                    else:
                        # If order is wrong, still use them but swap
                        response_state = [tactic_id, technique_id]
                elif technique_match:
                    # Only technique found, use default tactic
                    response_state = ['TA0001', technique_match.group(0)]
                else:
                    # Try splitting by space as fallback
                    parts = resp_clean.split()
                    for part in parts:
                        # Check if part is a tactic or technique ID
                        if re.match(r'TA\d+', part):
                            if not response_state:
                                response_state.append(part)
                            elif len(response_state) == 1:
                                response_state.insert(0, part)
                        elif re.match(r'T\d+', part) and part not in response_state:
                            response_state.append(part)
                            if len(response_state) == 1:
                                # If we only have technique, add default tactic
                                response_state.insert(0, 'TA0001')
                
                if len(response_state) < 2:
                    retry_count += 1
                    logger.warning(
                        "Could not parse state (attempt %d/%d); retrying",
                        retry_count,
                        max_retries,
                    )
                    time.sleep(1)
                    continue
            
            # Translate IDs to indices
            tacticID = ['TA0001','TA0002', 'TA0003', 'TA0004', 'TA0005', 'TA0006', 'TA0007', 'TA0008', 'TA0009', 'TA0011', 'TA0010', 'TA0040']
            techniqueID = ['T1548', 'T1134', 'T1531', 'T1087', 'T1098', 'T1650', 'T1583', 'T1595', 'T1557', 'T1071', 'T1010', 'T1560', 'T1123', 'T1119', 'T1020', 'T1197', 'T1547', 'T1037', 'T1176', 'T1217', 'T1185', 'T1110', 'T1612', 'T1115', 'T1651', 'T1580', 'T1538', 'T1526', 'T1619', 'T1059', 'T1092', 'T1586', 'T1554', 'T1584', 'T1609', 'T1613', 'T1659', 'T1136', 'T1543', 'T1555', 'T1485', 'T1132', 'T1486', 'T1530', 'T1602', 'T1213', 'T1005', 'T1039', 'T1025', 'T1565', 'T1001', 'T1074', 'T1030', 'T1622', 'T1491', 'T1140', 'T1610', 'T1587', 'T1652', 'T1006', 'T1561', 'T1484', 'T1482', 'T1189', 'T1568', 'T1114', 'T1573', 'T1499', 'T1611', 'T1585', 'T1546', 'T1480', 'T1048', 'T1041', 'T1011', 'T1052', 'T1567', 'T1190', 'T1203', 'T1212', 'T1211', 'T1068', 'T1210', 'T1133', 'T1008', 'T1083', 'T1222', 'T1657', 'T1495', 'T1187', 'T1606', 'T1592', 'T1589', 'T1590', 'T1591', 'T1615', 'T1200', 'T1564', 'T1665', 'T1574', 'T1562', 'T1656', 'T1525', 'T1070', 'T1202', 'T1105', 'T1490', 'T1056', 'T1559', 'T1534', 'T1570', 'T1654', 'T1036', 'T1556', 'T1578', 'T1112', 'T1601', 'T1111', 'T1621', 'T1104', 'T1106', 'T1599', 'T1498', 'T1046', 'T1135', 'T1040', 'T1095', 'T1571', 'T1027', 'T1588', 'T1137', 'T1003', 'T1201', 'T1120', 'T1069', 'T1566', 'T1598', 'T1647', 'T1653', 'T1542', 'T1057', 'T1055', 'T1572', 'T1090', 'T1012', 'T1620', 'T1219', 'T1563', 'T1021', 'T1018', 'T1091', 'T1496', 'T1207', 'T1014', 'T1053', 'T1029', 'T1113', 'T1597', 'T1596', 'T1593', 'T1594', 'T1505', 'T1648', 'T1489', 'T1129', 'T1072', 'T1518', 'T1608', 'T1528', 'T1649', 'T1558', 'T1539', 'T1553', 'T1195', 'T1218', 'T1082', 'T1614', 'T1016', 'T1049', 'T1033', 'T1216', 'T1007', 'T1569', 'T1529', 'T1124', 'T1080', 'T1221', 'T1205', 'T1537', 'T1127', 'T1199', 'T1552', 'T1535', 'T1550', 'T1204', 'T1078', 'T1125', 'T1497', 'T1600', 'T1102', 'T1047', 'T1220']
            
            if len(response_state) < 2:
                logger.error(
                    "Failed to parse state after %d attempts; using defaults",
                    max_retries,
                )
                tactic = 'TA0001'
                technique = 'T1003'  # Default technique
            else:
                tactic = response_state[0].strip()
                technique = response_state[1].strip()
            
            # Clean technique ID (remove .XXX suffix if present)
            if len(technique) > 5:
                technique = technique[:5]
            
            logger.debug("Parsed state: tactic=%s technique=%s", tactic, technique)
            
            tactic_id = tacticID.index(tactic) if tactic in tacticID else 1
            technique_id = techniqueID.index(technique) if technique in techniqueID else 1
            
            if tactic not in tacticID:
                logger.warning("Unknown tactic %s; using default index 1", tactic)
            if technique not in techniqueID:
                logger.warning("Unknown technique %s; using default index 1", technique)
            
            logger.info("Detected state: tactic=%d technique=%d", tactic_id, technique_id)
            
            # Check if episode should end (e.g., command buffer empty and no more techniques)
            # Or you can add other conditions here
            if not attacker.command_buffer and step >= 5:  # Minimum steps per episode
                logger.info("Episode %d completed after %d steps", episode + 1, step)
                break
    
    attacker.close()
    logger.info("Attack sequence completed")


def main():
    """
    Main function to run both honeypot and attacker in the same process.
    They will share the same LLM instance to save GPU memory.
    """
    configure_logging(log_file="application.log")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Unified Honeypot and Attacker Server')
    parser.add_argument('--mode', type=str, choices=['train', 'test'], default='train',
                        help='Mode: train (training mode) or test (test mode with loaded model)')
    parser.add_argument('--port', type=int, default=2222,
                        help='SSH server port (default: 2222, use 22 for standard SSH but requires root)')
    parser.add_argument('--model', type=str, default="../models/Llama-3.1-8B",
                        help='LLM model name or path (default: ../models/Llama-3.1-8B)')
    parser.add_argument('--model-type', type=str, choices=['local', 'openai'], default='local',
                        help='Model type: local or openai (default: local)')
    parser.add_argument('--enable-attacker', action='store_true', default=True,
                        help='Enable attacker (default: True)')
    parser.add_argument('--enable-honeypot', action='store_true', default=True,
                        help='Enable honeypot server (default: True)')
    args = parser.parse_args()
    
    # Initialize all services using InitializationManager (shared LLM)
    logger.info("Initializing services with a shared LLM instance")
    init_manager = InitializationManager(
        model_name=args.model,
        model_type=args.model_type,
        mode=args.mode,
        ssh_port=args.port,
        use_shared_llm=True  # Enable shared LLM
    )
    init_manager.initialize_all()
    
    # Print summary
    summary = init_manager.get_summary()
    logger.info("Initialization summary")
    for key, value in summary.items():
        logger.info("%s=%s", key, value)
    
    # Create threads for honeypot and attacker
    threads = []
    
    # Start honeypot server in a separate thread
    if args.enable_honeypot:
        honeypot_thread = threading.Thread(
            target=run_honeypot_server,
            args=(init_manager, args.port),
            daemon=True,
            name="HoneypotServer"
        )
        honeypot_thread.start()
        threads.append(honeypot_thread)
        logger.info(
            "Honeypot server started on port %d (thread=%s)",
            args.port,
            honeypot_thread.name,
        )
    
    # Give honeypot server time to start
    time.sleep(2)
    
    # Start attacker in a separate thread
    if args.enable_attacker:
        attacker_thread = threading.Thread(
            target=run_attacker,
            args=(init_manager,),
            daemon=True,
            name="Attacker"
        )
        attacker_thread.start()
        threads.append(attacker_thread)
        logger.info("Attacker started (thread=%s)", attacker_thread.name)
    
    logger.info("Attacker and honeypot are running with a shared LLM instance")
    
    # Keep main thread alive
    try:
        # Wait for all threads
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down; shared LLM will be cleaned up automatically")


if __name__ == "__main__":
    main()
