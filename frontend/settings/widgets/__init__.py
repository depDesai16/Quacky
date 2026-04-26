__all__ = ["ToggleSlider"]


def __getattr__(name: str):
    if name == "ToggleSlider":
        from .toggle_slider import ToggleSlider

        return ToggleSlider
    raise AttributeError(name)
