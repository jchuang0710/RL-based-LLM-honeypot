__all__ = ["HoneypotService", "HoneypotEnv"]


def __getattr__(name):
    if name in __all__:
        from src.honeypot.service import HoneypotEnv, HoneypotService

        return {
            "HoneypotService": HoneypotService,
            "HoneypotEnv": HoneypotEnv,
        }[name]
    raise AttributeError(name)
