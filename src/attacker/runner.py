"""Automated SSH honeypot evaluation runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import time

from src.attacker.service import AttackerSSHService
from src.shared.paths import ANALYSIS_OUTPUT_DIR, ensure_runtime_directories

logger = logging.getLogger(__name__)


@dataclass
class InteractionResult:
    episode: int
    step: int
    technique: str
    command: str
    response: str
    tactic: str
    detected_technique: str
    classification_checked: bool
    is_honeypot: bool
    duration_seconds: float
    timestamp: str


class AttackerEvaluationRunner:
    """Drive an SSH target and record structured evaluation results."""

    def __init__(
        self,
        attacker: AttackerSSHService,
        *,
        episodes=1,
        max_steps=20,
        initial_commands=None,
        detect_every=1,
        reconnect_each_episode=True,
        stop_on_honeypot=False,
        output_file=None,
    ):
        self.attacker = attacker
        self.episodes = episodes
        self.max_steps = max_steps
        self.initial_commands = initial_commands or ["whoami", "pwd", "uname -a"]
        self.detect_every = max(1, detect_every)
        self.reconnect_each_episode = reconnect_each_episode
        self.stop_on_honeypot = stop_on_honeypot
        ensure_runtime_directories()
        self.output_file = Path(output_file) if output_file else self._default_output_file()
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def run(self):
        results = []
        stop_evaluation = False

        for episode in range(1, self.episodes + 1):
            if episode > 1 and self.reconnect_each_episode:
                self.attacker.reconnect()
            self.attacker.reset(list(self.initial_commands))
            logger.info(
                "Starting SSH evaluation episode %d/%d against %s:%d",
                episode,
                self.episodes,
                self.attacker.hostname,
                self.attacker.port,
            )

            current_technique = "initial-discovery"
            for step in range(1, self.max_steps + 1):
                if not self.attacker.command_buffer:
                    current_technique = self.attacker.get_next_attack_technique()
                    self.attacker.command_buffer = (
                        self.attacker.get_commands_for_technique(current_technique)
                    )

                command = self.attacker.command_buffer.pop(0)
                started_at = time.monotonic()
                response = self.attacker.execute_command(command)
                duration = time.monotonic() - started_at
                self.attacker.add_interaction(command, response)

                state = self.attacker.detect_state(command)
                should_detect = step % self.detect_every == 0
                is_honeypot = (
                    self.attacker.detect_honeypot() if should_detect else False
                )

                result = InteractionResult(
                    episode=episode,
                    step=step,
                    technique=current_technique,
                    command=command,
                    response=response,
                    tactic=state["tactic"],
                    detected_technique=state["technique"],
                    classification_checked=should_detect,
                    is_honeypot=is_honeypot,
                    duration_seconds=round(duration, 4),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                results.append(result)
                self._write_result(result)
                logger.info(
                    "Evaluation step complete: episode=%d step=%d tactic=%s "
                    "technique=%s honeypot=%s duration=%.2fs",
                    episode,
                    step,
                    result.tactic,
                    result.detected_technique,
                    is_honeypot,
                    duration,
                )

                if is_honeypot and self.stop_on_honeypot:
                    logger.warning("Target classified as honeypot; stopping evaluation")
                    stop_evaluation = True
                    break

            if stop_evaluation:
                break

        summary = self._build_summary(results)
        summary_path = self.output_file.with_suffix(".summary.json")
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Evaluation results written to %s", self.output_file)
        logger.info("Evaluation summary written to %s", summary_path)
        return summary

    def _write_result(self, result):
        with self.output_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    def _build_summary(self, results):
        classification_checks = sum(
            result.classification_checked for result in results
        )
        honeypot_detections = sum(result.is_honeypot for result in results)
        return {
            "target": {
                "host": self.attacker.hostname,
                "port": self.attacker.port,
                "username": self.attacker.username,
            },
            "episodes_requested": self.episodes,
            "steps_executed": len(results),
            "classification_checks": classification_checks,
            "honeypot_detections": honeypot_detections,
            "honeypot_detection_rate": (
                honeypot_detections / classification_checks
                if classification_checks
                else 0.0
            ),
            "unknown_techniques": self.attacker.unknown_technique,
            "result_file": str(self.output_file),
        }

    def _default_output_file(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_host = self.attacker.hostname.replace(":", "_").replace("/", "_")
        return ANALYSIS_OUTPUT_DIR / f"attacker_{safe_host}_{self.attacker.port}_{timestamp}.jsonl"
