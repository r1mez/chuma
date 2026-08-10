"""Serialization of Agent lifecycle events for transport layers."""

from __future__ import annotations

import json
from typing import Any


class EventSerializer:
    """Keep SSE framing out of Agent business and runtime code."""

    @staticmethod
    def to_sse(event: dict[str, Any]) -> str:
        event_id = event.get("event_id", "")
        event_name = event.get("event", "message")
        return (
            f"id: {event_id}\n"
            f"event: {event_name}\n"
            f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        )

    @staticmethod
    def error(message: str) -> str:
        return f"data: {json.dumps({'type': 'error', 'content': message}, ensure_ascii=False)}\n\n"

    @staticmethod
    def done() -> str:
        return "data: [DONE]\n\n"
