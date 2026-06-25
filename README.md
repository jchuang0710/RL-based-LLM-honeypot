# RL-based LLM Honeypot

The application is separated into attacker and honeypot components under
`src/`.

## Project layout

```text
src/
  attacker/   # attack planning, Atomic Red Team commands, attacker entrypoint
  honeypot/   # SSH honeypot, RL environment, honeypot entrypoint
  shared/     # configuration, LLM integration, prompts, filesystem paths
  rl/         # DQN and DDQN implementations
  api/        # FastAPI application
  main.py     # run attacker and honeypot together
prompts/      # all LLM prompt templates
logs/         # attacker, honeypot, and training logs
outputs/      # checkpoints, rewards, analysis, and runtime artifacts
```

## Installation

```bash
pip install -r requirements.txt
```

Set `OPENAI_API_KEY` when using an OpenAI model.

## Run

Run commands from the repository root:

```bash
python -m src.honeypot.main --mode train --port 2222
python -m src.main --mode train --port 2222
python -m src.api.run --port 8000
```

Connect to the SSH honeypot:

```bash
ssh -T -p 2222 root@localhost
```

Runtime paths are defined centrally in `src/shared/paths.py`.

## Evaluate an SSH honeypot

The attacker can connect to any SSH-compatible honeypot by IP address and port.
Only run it against systems you own or are authorized to evaluate.

Password authentication:

```bash
set HONEYPOT_SSH_PASSWORD=password
python -m src.attacker.main \
  --host 192.168.1.50 \
  --port 2222 \
  --username root \
  --episodes 3 \
  --max-steps 20
```

Private-key authentication:

```bash
python -m src.attacker.main \
  --host 192.168.1.50 \
  --port 22 \
  --username evaluator \
  --key-file ~/.ssh/id_ed25519
```

OpenAI-based evaluation:

```bash
python -m src.attacker.main \
  --host 127.0.0.1 \
  --port 2222 \
  --username root \
  --model-type openai \
  --model gpt-4o-mini
```

Results are saved as JSONL plus a summary JSON under `outputs/analysis/`.
Useful options include `--command-timeout`, `--idle-timeout`,
`--detect-every`, `--stop-on-honeypot`, and repeatable
`--initial-command`.

## Logging

Application output uses Python's `logging` module instead of direct `print`
calls. Logs are written to the console and rotating files under `logs/`:

- `logs/application.log`
- `logs/attacker/application.log`
- `logs/honeypot/application.log`
- `logs/api.log`

Logging configuration is centralized in `src/shared/logging.py`.
