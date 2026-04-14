"""WhatsApp Web DOM selectors.

Centralized selectors for easy updates when WhatsApp UI changes.
Based on research.md selector strategy using data-testid and ARIA labels.
"""


class Selectors:
    """WhatsApp Web DOM selectors.

    Note: These selectors are subject to change when WhatsApp updates their UI.
    All selectors are centralized here for easy maintenance.
    """

    # Main interface detection
    QR_CODE = 'canvas[aria-label="Scan me!"]'
    MAIN_INTERFACE = '[data-testid="chat-list"]'

    # Chat list (left panel)
    CHAT_LIST = '[data-testid="chat-list"]'
    CHAT_ITEM = '[data-testid="cell-frame-container"]'
    UNREAD_BADGE = 'span[data-testid="icon-unread-count"]'
    CHAT_TITLE = '[data-testid="cell-frame-title"] span'

    # Alternative chat list selectors (fallback)
    CHAT_LIST_ALT = "#pane-side"
    UNREAD_BADGE_ALT = ".unread-count"

    # Conversation view (right panel)
    CONVERSATION_PANEL = '[data-testid="conversation-panel-messages"]'
    CONVERSATION_HEADER = '[data-testid="conversation-info-header"]'
    CONVERSATION_TITLE = '[data-testid="conversation-info-header-chat-title"]'

    # Message elements
    MESSAGE_ROW = '[data-testid="msg-container"]'
    MESSAGE_TEXT = "span.selectable-text"
    MESSAGE_TIME = '[data-testid="msg-time"]'
    MESSAGE_IN = ".message-in"  # Incoming messages
    MESSAGE_OUT = ".message-out"  # Outgoing messages (skip these)

    # Group chat indicators
    GROUP_ICON = '[data-testid="group"]'
    MESSAGE_AUTHOR = 'span[data-testid="author"]'

    # Media indicators
    MEDIA_IMAGE = '[data-testid="media-url-provider"]'
    MEDIA_DOCUMENT = '[data-testid="document-thumb"]'
    MEDIA_AUDIO = '[data-testid="audio-play"]'
    MEDIA_VIDEO = '[data-testid="video-play"]'

    # Loading states
    LOADING_SCREEN = '[data-testid="startup"]'
    CHAT_LOADING = '[data-testid="conversation-panel-wrapper"] [data-testid="status-v3-ring"]'


# Timeout values for different operations
class Timeouts:
    """Timeout values in milliseconds."""

    PAGE_LOAD = 30000  # Initial page load
    QR_SCAN = 120000  # Waiting for QR code scan (2 minutes)
    CHAT_OPEN = 5000  # Opening a chat conversation
    MESSAGE_LOAD = 3000  # Loading messages in a chat
    ELEMENT_VISIBLE = 2000  # Waiting for element visibility
