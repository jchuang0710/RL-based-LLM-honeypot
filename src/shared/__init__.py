__all__ = ["setting", "InitializationManager"]


def __getattr__(name):
    if name == "setting":
        from src.shared.config import setting

        return setting
    if name == "InitializationManager":
        from src.shared.initialization import InitializationManager

        return InitializationManager
    raise AttributeError(name)
