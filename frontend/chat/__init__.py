__all__ = ["QuackyWindow"]


def __getattr__(name: str):
    if name == "QuackyWindow":
        from .window import QuackyWindow

        return QuackyWindow
    raise AttributeError(name)
