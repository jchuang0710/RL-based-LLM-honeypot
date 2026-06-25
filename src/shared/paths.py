"""Centralized filesystem locations for the application."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
LOGS_DIR = PROJECT_ROOT / "logs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MODELS_DIR = PROJECT_ROOT / "models"
ATOMIC_RED_TEAM_DIR = PROJECT_ROOT / "atomic-red-team"

ATTACKER_LOGS_DIR = LOGS_DIR / "attacker"
HONEYPOT_LOGS_DIR = LOGS_DIR / "honeypot"
TRAINING_LOGS_DIR = LOGS_DIR / "training"

REWARDS_OUTPUT_DIR = OUTPUTS_DIR / "rewards"
CHECKPOINTS_OUTPUT_DIR = OUTPUTS_DIR / "checkpoints"
ANALYSIS_OUTPUT_DIR = OUTPUTS_DIR / "analysis"
RUNTIME_OUTPUT_DIR = OUTPUTS_DIR / "runtime"


def ensure_runtime_directories() -> None:
    """Create directories written by the application."""
    for directory in (
        ATTACKER_LOGS_DIR,
        HONEYPOT_LOGS_DIR,
        TRAINING_LOGS_DIR,
        REWARDS_OUTPUT_DIR,
        CHECKPOINTS_OUTPUT_DIR,
        ANALYSIS_OUTPUT_DIR,
        RUNTIME_OUTPUT_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
