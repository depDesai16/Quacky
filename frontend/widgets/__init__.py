__all__ = [
    "CardWidget",
    "HeaderBar", "StatusChip",
    "ChatTimeline",
    "UserBubble", "AssistantBubble",
    "Composer",
    "MicButton", "SendButton",
    "EmptyState",
    "ThinkingBubble",
    "Toast",
]


def __getattr__(name: str):
    if name == "CardWidget":
        from .card_widget import CardWidget

        return CardWidget
    if name == "HeaderBar":
        from .header_bar import HeaderBar

        return HeaderBar
    if name == "StatusChip":
        from .header_bar import StatusChip

        return StatusChip
    if name == "ChatTimeline":
        from .chat_timeline import ChatTimeline

        return ChatTimeline
    if name == "UserBubble":
        from .message_bubble import UserBubble

        return UserBubble
    if name == "AssistantBubble":
        from .message_bubble import AssistantBubble

        return AssistantBubble
    if name == "Composer":
        from .composer import Composer

        return Composer
    if name == "MicButton":
        from .icon_buttons import MicButton

        return MicButton
    if name == "SendButton":
        from .icon_buttons import SendButton

        return SendButton
    if name == "EmptyState":
        from .empty_state import EmptyState

        return EmptyState
    if name == "ThinkingBubble":
        from .thinking_bubble import ThinkingBubble

        return ThinkingBubble
    if name == "Toast":
        from .toast import Toast

        return Toast
    raise AttributeError(name)
