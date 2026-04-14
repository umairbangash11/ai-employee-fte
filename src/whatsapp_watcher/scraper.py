"""WhatsApp Web scraping for unread messages.

Extracts message data from WhatsApp Web using Playwright DOM queries.
"""

import asyncio
import re
import sys
from datetime import datetime, timedelta

from playwright.async_api import ElementHandle, Page, TimeoutError as PlaywrightTimeoutError

from .config import WatcherConfig
from .models import WhatsAppMessage
from .selectors import Selectors, Timeouts


async def get_unread_chat_elements(page: Page) -> list[ElementHandle]:
    """Find all chat items with unread badges.

    Args:
        page: Playwright page with WhatsApp Web loaded

    Returns:
        List of chat item element handles with unread badges
    """
    try:
        # Query all chat items
        chat_items = await page.query_selector_all(Selectors.CHAT_ITEM)

        unread_chats = []
        for chat_item in chat_items:
            # Check if this chat has an unread badge
            unread_badge = await chat_item.query_selector(Selectors.UNREAD_BADGE)
            if unread_badge:
                unread_chats.append(chat_item)

        return unread_chats
    except Exception as e:
        print(f"Error finding unread chats: {e}", file=sys.stderr)
        return []


async def extract_chat_info(chat_element: ElementHandle) -> dict:
    """Extract chat metadata from chat list item.

    Args:
        chat_element: Chat item element handle

    Returns:
        Dict with chat_name, chat_type, unread_count
    """
    try:
        # Extract chat name
        title_element = await chat_element.query_selector(Selectors.CHAT_TITLE)
        chat_name = "Unknown"
        if title_element:
            chat_name = (await title_element.text_content()) or "Unknown"
            chat_name = chat_name.strip()

        # Detect if group (check for group icon)
        group_icon = await chat_element.query_selector(Selectors.GROUP_ICON)
        chat_type = "group" if group_icon else "individual"

        # Extract unread count (optional)
        unread_count = 0
        unread_badge = await chat_element.query_selector(Selectors.UNREAD_BADGE)
        if unread_badge:
            count_text = (await unread_badge.text_content()) or "0"
            try:
                unread_count = int(count_text.strip())
            except ValueError:
                unread_count = 1  # Default to 1 if can't parse

        return {
            "chat_name": chat_name,
            "chat_type": chat_type,
            "unread_count": unread_count
        }
    except Exception as e:
        print(f"Error extracting chat info: {e}", file=sys.stderr)
        return {
            "chat_name": "Unknown",
            "chat_type": "individual",
            "unread_count": 0
        }


def parse_message_timestamp(time_str: str) -> datetime:
    """Parse WhatsApp Web timestamp to datetime.

    WhatsApp shows times as:
        - "14:30" (today)
        - "Yesterday"
        - "DD/MM/YYYY"

    Args:
        time_str: Timestamp string from WhatsApp

    Returns:
        Best-effort datetime (may use current date for "HH:MM" format)
    """
    time_str = time_str.strip()
    now = datetime.now()

    # Try HH:MM format (today)
    if re.match(r'^\d{1,2}:\d{2}$', time_str):
        try:
            time_parts = time_str.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, IndexError):
            return now

    # Try "Yesterday"
    if time_str.lower() == "yesterday":
        yesterday = now - timedelta(days=1)
        return yesterday.replace(hour=12, minute=0, second=0, microsecond=0)

    # Try DD/MM/YYYY format
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', time_str):
        try:
            parts = time_str.split('/')
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            return datetime(year, month, day, 12, 0, 0)
        except (ValueError, IndexError):
            return now

    # Fallback: return current time
    return now


async def detect_media_type(message_element: ElementHandle) -> tuple[bool, str | None]:
    """Detect if message contains media and its type.

    Args:
        message_element: Message row element handle

    Returns:
        (has_media: bool, media_type: str | None)
        media_type in ["image", "video", "audio", "document", None]
    """
    try:
        # Check for different media types
        if await message_element.query_selector(Selectors.MEDIA_IMAGE):
            return (True, "image")
        if await message_element.query_selector(Selectors.MEDIA_VIDEO):
            return (True, "video")
        if await message_element.query_selector(Selectors.MEDIA_AUDIO):
            return (True, "audio")
        if await message_element.query_selector(Selectors.MEDIA_DOCUMENT):
            return (True, "document")

        return (False, None)
    except Exception:
        return (False, None)


async def extract_messages_from_conversation(
    page: Page,
    chat_name: str,
    chat_type: str
) -> list[WhatsAppMessage]:
    """Extract messages from open conversation panel.

    Args:
        page: Playwright page with conversation open
        chat_name: Name of the chat
        chat_type: "individual" or "group"

    Returns:
        List of WhatsAppMessage instances
    """
    messages = []

    try:
        # Wait for messages to load
        await page.wait_for_selector(Selectors.MESSAGE_ROW, timeout=Timeouts.MESSAGE_LOAD)

        # Query all message rows
        message_rows = await page.query_selector_all(Selectors.MESSAGE_ROW)

        for message_row in message_rows:
            try:
                # Filter to incoming messages only (skip outgoing)
                is_outgoing = await message_row.query_selector(Selectors.MESSAGE_OUT)
                if is_outgoing:
                    continue  # Skip outgoing messages

                # Extract message text
                text_element = await message_row.query_selector(Selectors.MESSAGE_TEXT)
                body = ""
                if text_element:
                    body = (await text_element.text_content()) or ""
                    body = body.strip()

                if not body:
                    # Skip empty messages (might be media-only or deleted)
                    continue

                # Extract timestamp
                time_element = await message_row.query_selector(Selectors.MESSAGE_TIME)
                timestamp = datetime.now()
                if time_element:
                    time_str = (await time_element.text_content()) or ""
                    timestamp = parse_message_timestamp(time_str)

                # Extract sender (for group chats)
                sender = chat_name  # Default to chat name
                if chat_type == "group":
                    author_element = await message_row.query_selector(Selectors.MESSAGE_AUTHOR)
                    if author_element:
                        sender = (await author_element.text_content()) or chat_name
                        sender = sender.strip()

                # Detect media
                has_media, media_type = await detect_media_type(message_row)

                # Build WhatsAppMessage
                message = WhatsAppMessage(
                    chat_name=chat_name,
                    chat_type=chat_type,
                    sender=sender,
                    timestamp=timestamp,
                    body=body,
                    has_media=has_media,
                    media_type=media_type
                )

                messages.append(message)

            except Exception as e:
                print(f"Error extracting message: {e}", file=sys.stderr)
                continue

    except PlaywrightTimeoutError:
        print(f"Timeout waiting for messages in {chat_name}", file=sys.stderr)
    except Exception as e:
        print(f"Error extracting messages from {chat_name}: {e}", file=sys.stderr)

    return messages


async def scrape_unread_messages(
    page: Page,
    config: WatcherConfig
) -> list[WhatsAppMessage]:
    """Scrape all unread messages from WhatsApp Web.

    Algorithm:
        1. Query chat list for items with unread badges
        2. For each unread chat:
            a. Click to open conversation
            b. Wait for messages to load
            c. Extract message elements
            d. Parse each message to WhatsAppMessage
            e. Navigate back to chat list
        3. Return all extracted messages

    Args:
        page: Playwright page with WhatsApp Web loaded
        config: WatcherConfig with settings

    Returns:
        List of WhatsAppMessage instances (may be empty)
    """
    all_messages = []

    # Retry wrapper for transient failures
    async def scrape_with_retry() -> list[WhatsAppMessage]:
        for attempt in range(3):
            try:
                # Find unread chats
                unread_chats = await get_unread_chat_elements(page)
                print(f"Found {len(unread_chats)} unread chats", file=sys.stderr)

                if not unread_chats:
                    return []

                messages_batch = []

                for i, chat_element in enumerate(unread_chats):
                    try:
                        # Extract chat info
                        chat_info = await extract_chat_info(chat_element)
                        chat_name = chat_info["chat_name"]
                        chat_type = chat_info["chat_type"]

                        print(f"Opening chat {i+1}/{len(unread_chats)}: {chat_name}", file=sys.stderr)

                        # Click chat to open
                        await chat_element.click()

                        # Wait for conversation panel to load
                        await page.wait_for_selector(Selectors.CONVERSATION_PANEL, timeout=Timeouts.CHAT_OPEN)

                        # Extract messages
                        messages = await extract_messages_from_conversation(page, chat_name, chat_type)
                        print(f"Extracted {len(messages)} messages from {chat_name}", file=sys.stderr)

                        messages_batch.extend(messages)

                        # Navigate back to chat list
                        await page.wait_for_selector(Selectors.CHAT_LIST, timeout=Timeouts.ELEMENT_VISIBLE)

                    except Exception as e:
                        print(f"Error processing chat: {e}", file=sys.stderr)
                        # Try to recover by waiting for chat list
                        try:
                            await page.wait_for_selector(Selectors.CHAT_LIST, timeout=Timeouts.ELEMENT_VISIBLE)
                        except Exception:
                            pass
                        continue

                return messages_batch

            except Exception as e:
                if attempt < 2:
                    delay = 2 ** attempt  # 1s, 2s
                    print(f"Scrape attempt {attempt+1}/3 failed: {e}. Retrying in {delay}s...", file=sys.stderr)
                    await asyncio.sleep(delay)
                else:
                    print(f"Scrape failed after 3 attempts: {e}", file=sys.stderr)
                    raise

        return []

    try:
        all_messages = await scrape_with_retry()
    except Exception as e:
        print(f"Scraper error: {e}", file=sys.stderr)
        all_messages = []

    return all_messages
