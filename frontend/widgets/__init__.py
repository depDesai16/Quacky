"""widgets package — all UI component classes for Quacky."""

from .card_widget    import CardWidget
from .header_bar     import HeaderBar, StatusChip
from .chat_timeline  import ChatTimeline
from .message_bubble import UserBubble, AssistantBubble
from .composer       import Composer
from .icon_buttons   import MicButton, SendButton
from .empty_state    import EmptyState
from .thinking_bubble import ThinkingBubble
from .toast          import Toast

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