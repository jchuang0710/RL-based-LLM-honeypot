"""
Honeypot main - Runs the honeypot server
This script represents the honeypot's perspective:
- Receives commands from attackers
- Uses RL agent to select actions
- Generates responses using LLM
- Learns from interactions

Usage:
    python -m src.honeypot.main [--mode train|test]
    
    --mode: 'train' for training mode, 'test' for test mode (default: 'train')
"""
import argparse
import logging
from src.honeypot.ssh_server import start_ssh_server
from src.shared import InitializationManager
from src.shared.logging import configure_logging

logger = logging.getLogger(__name__)

def main():
    """
    Start honeypot server.
    The server will:
    1. Accept SSH connections
    2. Use RL agent to select actions based on state
    3. Generate responses using LLM
    4. Learn from interactions
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Honeypot Server')
    parser.add_argument('--mode', type=str, choices=['train', 'test'], default='train',
                        help='Mode: train (training mode) or test (test mode with loaded model)')
    parser.add_argument('--port', type=int, default=2222,
                        help='SSH server port (default: 2222, use 22 for standard SSH but requires root)')
    parser.add_argument('--model', type=str, default="../models/Llama-3.1-8B",
                        help='LLM model name or path (default: ../models/Llama-3.1-8B)')
    parser.add_argument('--model-type', type=str, choices=['local', 'openai'], default='local',
                        help='Model type: local or openai (default: local)')
    args = parser.parse_args()
    
    # Initialize all services using InitializationManager
    configure_logging(log_file="honeypot/application.log")
    logger.info("Initializing honeypot services")
    init_manager = InitializationManager(
        model_name=args.model,
        model_type=args.model_type,
        mode=args.mode,
        ssh_port=args.port
    )
    init_manager.initialize_all()
    
    # Print summary
    summary = init_manager.get_summary()
    logger.info("Honeypot initialization summary")
    for key, value in summary.items():
        logger.info("%s=%s", key, value)
    
    logger.info("Starting honeypot SSH server")
    
    # Start SSH server (this handles connections and uses RL agent internally)
    # Pass DQN instance to use the shared one from initialization manager
    start_ssh_server(init_manager.llm_service, port=args.port, dqn_instance=init_manager.dqn)


if __name__ == "__main__":
    main()
