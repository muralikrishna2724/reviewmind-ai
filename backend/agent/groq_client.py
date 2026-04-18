"""Groq LLM client with retry and text-only fallback.

Retry policy:
  Attempt 1: function calling mode
  Attempt 2: function calling mode (retry on JSON parse failure)
  Attempt 3: text-only fallback
  After 3 failures: return GroqError (never raise)
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from groq import Groq, APIError

logger = logging.getLogger(__name__)


@dataclass
class GroqError:
    message: str
    raw_response: str = ""


def _client() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def _model() -> str:
    return os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


async def call_with_tools(
    system: str,
    user: str,
    tools: list[dict[str, Any]],
) -> dict[str, Any] | GroqError:
    """Call Groq with function calling. Retries once, then falls back to text-only."""
    client = _client()
    model = _model()

    for attempt in range(1, 3):  # attempts 1 and 2 use function calling
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                tools=tools,
                tool_choice="auto",
            )
            # Extract tool call arguments
            message = response.choices[0].message
            if message.tool_calls:
                raw = message.tool_calls[0].function.arguments
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as exc:
                    logger.error(
                        "Groq JSON parse failure (attempt %d): %s | raw: %s",
                        attempt, exc, raw,
                    )
                    # fall through to retry
                    continue
            # No tool call — treat content as JSON
            content = message.content or ""
            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                logger.error(
                    "Groq content JSON parse failure (attempt %d): %s | raw: %s",
                    attempt, exc, content,
                )
                continue
        except APIError as exc:
            logger.error("Groq API error (attempt %d): %s", attempt, exc)
            return GroqError(message=str(exc), raw_response=str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.error("Groq unexpected error (attempt %d): %s", attempt, exc)
            return GroqError(message=str(exc))

    # Both function-calling attempts failed — fall back to text-only
    logger.warning("Groq function calling failed after 2 attempts, falling back to text-only")
    return await call_text_only(system, user)


async def call_text_only(system: str, user: str) -> str | GroqError:
    """Text-only Groq call (no function calling). Last resort fallback."""
    client = _client()
    model = _model()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
    except APIError as exc:
        logger.error("Groq text-only API error: %s", exc)
        return GroqError(message=str(exc), raw_response=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("Groq text-only unexpected error: %s", exc)
        return GroqError(message=str(exc))
