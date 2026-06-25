__all__ = ["AttackerService", "AttackerSSHService"]


def __getattr__(name):
    if name in __all__:
        from src.attacker.service import AttackerSSHService, AttackerService

        return {
            "AttackerService": AttackerService,
            "AttackerSSHService": AttackerSSHService,
        }[name]
    raise AttributeError(name)
