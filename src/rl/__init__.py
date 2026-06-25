__all__ = ["BaseDQN", "Net", "DQN", "DDQN"]


def __getattr__(name):
    if name in {"BaseDQN", "Net"}:
        from src.rl.base import BaseDQN, Net

        return {"BaseDQN": BaseDQN, "Net": Net}[name]
    if name == "DQN":
        from src.rl.dqn import DQN

        return DQN
    if name == "DDQN":
        from src.rl.ddqn import DDQN

        return DDQN
    raise AttributeError(name)
