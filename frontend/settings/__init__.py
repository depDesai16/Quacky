__all__ = ["SettingsController", "SettingsPanel"]


def __getattr__(name: str):
    if name == "SettingsController":
        from .controller import SettingsController

        return SettingsController
    if name == "SettingsPanel":
        from .view import SettingsPanel

        return SettingsPanel
    raise AttributeError(name)
