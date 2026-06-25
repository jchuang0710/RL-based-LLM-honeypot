"""Load Atomic Red Team commands and lifecycle attack sequences."""

from __future__ import annotations

from functools import lru_cache
import glob
import logging
from pathlib import Path
import random
import re
from typing import Any

import pandas as pd
import yaml

from src.shared import setting
from src.shared.paths import ATOMIC_RED_TEAM_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

random.seed(10 if setting.mode == "train" else 11)

ATOMS_DIR = ATOMIC_RED_TEAM_DIR / "atomics"
LIFECYCLE_PATH = PROJECT_ROOT / "config" / "lifecycle.xlsx"
VICTIM_PATHS = {
    "linux": "/home/atomics",
    "windows": r"C:\atomics",
}
PLACEHOLDER_PATTERN = re.compile(r"#\{(\w+)\}")


def replace_placeholders(data: Any, input_arguments: dict[str, str]) -> Any:
    """Replace Atomic Red Team ``#{name}`` placeholders recursively."""
    if isinstance(data, dict):
        return {key: replace_placeholders(value, input_arguments) for key, value in data.items()}
    if isinstance(data, list):
        return [replace_placeholders(value, input_arguments) for value in data]
    if isinstance(data, str):
        return PLACEHOLDER_PATTERN.sub(
            lambda match: input_arguments.get(match.group(1), match.group(0)),
            data,
        )
    return data


def load_yaml(file_path: str | Path) -> dict[str, Any]:
    """Load an Atomic Red Team YAML file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Atomic Red Team YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _find_atomic_files() -> list[str]:
    patterns = [
        str(ATOMS_DIR / "T*" / "*.yaml").replace("\\", "/"),
        str(ATOMS_DIR / "T*" / "*.yaml"),
        str(ATOMS_DIR / "**" / "*.yaml").replace("\\", "/"),
    ]
    for index, pattern in enumerate(patterns):
        files = glob.glob(pattern, recursive=index == 2)
        if index == 2:
            files = [
                file_path
                for file_path in files
                if Path(file_path).parent.name.startswith("T")
            ]
        if files:
            return sorted(files)

    logger.warning(
        "No Atomic Red Team YAML files found in %s; searched=%s",
        ATOMS_DIR,
        patterns,
    )
    return []


def _append_commands(
    command_set: list[str],
    command_text: str,
    arguments: dict[str, str],
    victim_path: str,
) -> None:
    expanded = replace_placeholders(command_text, arguments).replace(
        "PathToAtomicsFolder",
        victim_path,
    )
    command_set.extend(
        line for line in expanded.splitlines() if line and not line.startswith("#")
    )


@lru_cache(maxsize=2)
def _get_technique_command(system: str) -> dict[str, list[list[str]]]:
    """Build the technique-to-command mapping once per operating system."""
    victim_path = VICTIM_PATHS[system]
    technique_commands: dict[str, list[list[str]]] = {}
    files = _find_atomic_files()

    for file_path in files:
        yaml_data = load_yaml(file_path)
        technique = yaml_data["attack_technique"]
        technique_commands.setdefault(technique, [])

        for test in yaml_data.get("atomic_tests", []):
            if system not in test.get("supported_platforms", []):
                continue

            command_set: list[str] = []
            arguments = {
                name: str(config.get("default", ""))
                for name, config in test.get("input_arguments", {}).items()
            }

            for dependency in test.get("dependencies", []):
                prerequisite = dependency.get("get_prereq_command")
                if prerequisite:
                    _append_commands(command_set, prerequisite, arguments, victim_path)

            command = test.get("executor", {}).get("command")
            if command:
                _append_commands(command_set, command, arguments, victim_path)

            if command_set:
                technique_commands[technique].append(command_set)

    logger.info(
        "Loaded %d Atomic Red Team techniques for %s from %d files",
        len(technique_commands),
        system,
        len(files),
    )
    return technique_commands


def get_technique_command() -> dict[str, list[list[str]]]:
    return _get_technique_command(setting.system)


@lru_cache(maxsize=1)
def get_lifecycle() -> dict[Any, list[str]]:
    """Load lifecycle technique sequences from the experiment workbook."""
    dataframe = pd.read_excel(LIFECYCLE_PATH)
    lifecycle: dict[Any, list[str]] = {}
    for lifecycle_id, technique in dataframe.values:
        lifecycle.setdefault(lifecycle_id, []).append(technique)
    return lifecycle


def get_lifecycle_command() -> list[str]:
    lifecycle = get_lifecycle()
    techniques = lifecycle[random.choice(list(lifecycle))]
    technique_commands = get_technique_command()
    commands: list[str] = []

    for technique in techniques:
        procedures = technique_commands.get(technique, [])
        if procedures:
            commands.extend(random.choice(procedures))
    return commands


def get_command(technique: str) -> list[str]:
    procedures = get_technique_command().get(technique, [])
    if not procedures:
        raise KeyError(f"No Atomic Red Team command found for technique {technique}")
    return list(random.choice(procedures))


def technique_exist(technique: str) -> bool:
    return bool(get_technique_command().get(technique))
