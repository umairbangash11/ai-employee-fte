"""LLM-based email classifier for Email Reasoning Layer.

Uses OpenAI GPT-4o to classify emails and extract actionable information.
Implements Ralph Wiggum Loop (3 retries with backoff) per Constitution Principle V.
"""

import json
import logging
import os
import time
from typing import Optional

from openai import OpenAI
from pydantic import ValidationError

from .models import EmailFile, ClassificationResult


logger = logging.getLogger(__name__)


# =============================================================================
# T034: System prompt for email classification
# =============================================================================

SYSTEM_PROMPT = """You are an email classification assistant. Your task is to analyze emails and classify them into exactly one category.

Categories:
1. actionable - Requires user response or action:
   - Direct personal or business communication requiring response
   - Job opportunities (applications, interviews, offers)
   - Payment or finance alerts (invoices, bills, transfers)
   - Invitations requiring RSVP (meetings, events, calls)
   - Requests with explicit deadlines or follow-up needed
   - Account security alerts (password reset, suspicious activity)

2. informational - FYI content, no action needed:
   - Order confirmations and shipping updates
   - Read receipts and delivery notifications
   - Automated reports and summaries
   - News digests from subscribed sources
   - System status notifications

3. promotional - Marketing and sales content:
   - Marketing emails and sales promotions
   - Newsletter content without personal relevance
   - Discount codes and offers
   - App feature announcements
   - Survey requests from brands

4. ignore - Low-value content:
   - Spam that passed filters
   - Duplicate notifications
   - Auto-replies and out-of-office messages
   - Unsubscribe confirmations
   - Generic platform notifications (social likes, follows)

For actionable emails, also extract:
- action: Clear 1-sentence description of required action
- priority: high (urgent/time-sensitive) | medium (important but not urgent) | low (can wait)
- due_date: ISO date (YYYY-MM-DD) if a deadline is mentioned, else null
- is_multi_step: true if multiple distinct actions are needed
- steps: Ordered list of steps if is_multi_step is true

Respond with JSON only. Do not include any text outside the JSON object."""


# =============================================================================
# T035: User prompt template
# =============================================================================

USER_PROMPT_TEMPLATE = """Classify this email:

From: {sender}
Subject: {subject}
Date: {date}
Body:
{body}

Respond with JSON matching this schema:
{{
  "classification": "actionable" | "informational" | "promotional" | "ignore",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation",
  "action": "Required action if actionable, else null",
  "priority": "high" | "medium" | "low" | null,
  "due_date": "YYYY-MM-DD" | null,
  "is_multi_step": true | false,
  "steps": ["step1", "step2"] | null
}}"""


# =============================================================================
# T033, T027: OpenAI client initialization
# =============================================================================

_client: Optional[OpenAI] = None


def get_openai_client(api_key: Optional[str] = None) -> OpenAI:
    """Get or create OpenAI client.

    Args:
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.

    Returns:
        Configured OpenAI client.

    Raises:
        ValueError: If no API key is available.
    """
    global _client

    if _client is not None:
        return _client

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is required but not set")

    _client = OpenAI(api_key=key)
    return _client


# =============================================================================
# T042: Body truncation for long emails
# =============================================================================

MAX_BODY_CHARS = 12000  # ~4000 tokens assuming 3 chars per token


def truncate_body(body: str, max_chars: int = MAX_BODY_CHARS) -> str:
    """Truncate email body to fit within token limits.

    Args:
        body: Original email body.
        max_chars: Maximum characters to keep.

    Returns:
        Truncated body with indicator if truncated.
    """
    if len(body) <= max_chars:
        return body

    truncated = body[:max_chars]
    # Try to truncate at a paragraph break
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars // 2:
        truncated = truncated[:last_para]

    return truncated + "\n\n[... email truncated for processing ...]"


# =============================================================================
# T036-T041: Email classification with retry and error handling
# =============================================================================


def classify_email(
    email: EmailFile,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    confidence_threshold: float = 0.6,
) -> ClassificationResult:
    """Classify an email using GPT-4o.

    Implements Ralph Wiggum Loop (Constitution Principle V):
    - Attempt 1: Full classification
    - Attempt 2: Retry with truncated body
    - Attempt 3: Classify based on subject only
    - After 3 failures: Return informational fallback

    Args:
        email: EmailFile to classify.
        api_key: OpenAI API key.
        model: Model to use (default: gpt-4o).
        confidence_threshold: Below this, fall back to informational.

    Returns:
        ClassificationResult with category and extracted info.
    """
    client = get_openai_client(api_key)

    # Prepare body (truncate if needed)
    body = truncate_body(email.body) if email.body else "(empty body)"

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        sender=email.sender or "Unknown",
        subject=email.subject or "No Subject",
        date=email.captured_at.isoformat() if email.captured_at else "Unknown",
        body=body,
    )

    # T040: Ralph Wiggum Loop - 3 attempts with backoff
    for attempt in range(1, 4):
        try:
            logger.debug(f"Classification attempt {attempt} for {email.message_id}")

            # T037: JSON mode for structured output
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temp for consistency
            )

            # Extract response content
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            # T038: Parse JSON response
            data = json.loads(content)

            # T038: Validate with Pydantic
            result = ClassificationResult(**data)

            # T039: Confidence threshold check
            if result.confidence < confidence_threshold:
                logger.info(
                    f"Low confidence ({result.confidence:.2f}) for {email.message_id}, "
                    f"falling back to informational"
                )
                return ClassificationResult(
                    classification="informational",
                    confidence=result.confidence,
                    reasoning=f"Low confidence classification: {result.reasoning}",
                )

            logger.info(
                f"Classified {email.message_id} as {result.classification} "
                f"(confidence: {result.confidence:.2f})"
            )
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt}: Invalid JSON response: {e}")
        except ValidationError as e:
            logger.warning(f"Attempt {attempt}: Invalid classification structure: {e}")
        except Exception as e:
            logger.warning(f"Attempt {attempt}: API error: {e}")

        # Backoff before retry
        if attempt < 3:
            sleep_time = 2 ** attempt  # 2s, 4s
            logger.debug(f"Retrying in {sleep_time}s...")
            time.sleep(sleep_time)

            # On attempt 2, try with subject only
            if attempt == 2:
                user_prompt = USER_PROMPT_TEMPLATE.format(
                    sender=email.sender or "Unknown",
                    subject=email.subject or "No Subject",
                    date=email.captured_at.isoformat() if email.captured_at else "Unknown",
                    body="(body not available - classify based on subject)",
                )

    # T041: After 3 failures, return informational fallback
    logger.error(f"All classification attempts failed for {email.message_id}")
    return ClassificationResult(
        classification="informational",
        confidence=0.0,
        reasoning="Classification failed after 3 attempts, defaulted to informational",
    )


def classify_batch(
    emails: list[EmailFile],
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> list[tuple[EmailFile, ClassificationResult]]:
    """Classify multiple emails.

    Args:
        emails: List of EmailFile objects to classify.
        api_key: OpenAI API key.
        model: Model to use.

    Returns:
        List of (EmailFile, ClassificationResult) tuples.
    """
    results = []
    for email in emails:
        result = classify_email(email, api_key, model)
        results.append((email, result))
    return results
