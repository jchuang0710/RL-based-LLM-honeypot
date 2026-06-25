"""Command-line SSH attacker for evaluating honeypots."""

from __future__ import annotations

import argparse
import logging
import os

from src.attacker.runner import AttackerEvaluationRunner
from src.attacker.service import AttackerSSHService
from src.shared import InitializationManager, setting
from src.shared.logging import configure_logging

logger = logging.getLogger(__name__)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Automatically interact with and evaluate an SSH honeypot"
    )
    parser.add_argument("--host", required=True, help="Target IP address or hostname")
    parser.add_argument("--port", type=int, default=22, help="Target SSH port")
    parser.add_argument("--username", default="root", help="SSH username")
    parser.add_argument(
        "--password",
        default=os.getenv("HONEYPOT_SSH_PASSWORD"),
        help="SSH password; defaults to HONEYPOT_SSH_PASSWORD",
    )
    parser.add_argument("--key-file", help="SSH private-key path")
    parser.add_argument("--connect-timeout", type=float, default=10.0)
    parser.add_argument("--command-timeout", type=float, default=15.0)
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=1.0,
        help="Finish reading after this many seconds without new output",
    )
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument(
        "--initial-command",
        action="append",
        dest="initial_commands",
        help="Initial discovery command; repeat to provide multiple commands",
    )
    parser.add_argument(
        "--detect-every",
        type=int,
        default=1,
        help="Run honeypot classification every N commands",
    )
    parser.add_argument("--stop-on-honeypot", action="store_true")
    parser.add_argument(
        "--keep-session",
        action="store_true",
        help="Reuse the same SSH session between episodes",
    )
    parser.add_argument("--output", help="JSONL evaluation output path")
    parser.add_argument("--system", choices=["linux", "windows"], default="linux")
    parser.add_argument("--model-type", choices=["local", "openai"], default="local")
    parser.add_argument("--model", help="Local model path/name or OpenAI model name")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    configure_logging(level=args.log_level.upper(), log_file="attacker/application.log")
    setting.system = args.system
    model_name = args.model or (
        "gpt-4o-mini-2024-07-18"
        if args.model_type == "openai"
        else "Llama-3.1-8B"
    )
    initial_commands = args.initial_commands
    if initial_commands is None:
        initial_commands = (
            ["whoami", "pwd", "uname -a"]
            if args.system == "linux"
            else ["whoami", "Get-Location", "systeminfo"]
        )

    logger.info("Initializing attacker LLM")
    init_manager = InitializationManager(
        model_name=model_name,
        model_type=args.model_type,
        mode="test",
    )
    llm = init_manager.llm_service

    attacker = AttackerSSHService(
        llm,
        hostname=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        key_filename=args.key_file,
        connect_timeout=args.connect_timeout,
        command_timeout=args.command_timeout,
        idle_timeout=args.idle_timeout,
    )
    try:
        runner = AttackerEvaluationRunner(
            attacker,
            episodes=args.episodes,
            max_steps=args.max_steps,
            initial_commands=initial_commands,
            detect_every=args.detect_every,
            reconnect_each_episode=not args.keep_session,
            stop_on_honeypot=args.stop_on_honeypot,
            output_file=args.output,
        )
        summary = runner.run()
        logger.info("Evaluation summary: %s", summary)
        return summary
    finally:
        attacker.close()


if __name__ == "__main__":
    main()
