__all__ = ["SpeechToSpeechPanel", "SpeechToSpeechController"]


def __getattr__(name: str):
    if name == "SpeechToSpeechPanel":
        from .sts_panel import SpeechToSpeechPanel

        return SpeechToSpeechPanel
    if name == "SpeechToSpeechController":
        from .controller import SpeechToSpeechController

        return SpeechToSpeechController
    raise AttributeError(name)
