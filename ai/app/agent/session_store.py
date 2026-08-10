"""Best-effort Redis persistence for Agent conversations and runs."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class AgentSessionStore:
    """Persist conversation history and event traces without blocking replies.

    Redis is intentionally optional. If it is not configured or temporarily
    unavailable, the Agent remains usable and the failure is logged.
    """

    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 30 * 24 * 3600):
        self.ttl_seconds = ttl_seconds
        self._redis = None
        url = redis_url if redis_url is not None else settings.REDIS_URL
        if url:
            self._redis = redis.from_url(url, decode_responses=True)

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    @staticmethod
    def _scope(user_id: int, user_role: str, conversation_id: str) -> str:
        return f"{user_role}:{user_id}:{conversation_id}"

    def _history_key(self, user_id: int, user_role: str, conversation_id: str) -> str:
        return f"agent:conversation:{self._scope(user_id, user_role, conversation_id)}:history"

    def _index_key(self, user_id: int, user_role: str) -> str:
        return f"agent:conversations:{user_role}:{user_id}:index"

    def _meta_key(self, user_id: int, user_role: str, conversation_id: str) -> str:
        return f"agent:conversation:{self._scope(user_id, user_role, conversation_id)}:meta"

    def _run_key(
        self,
        user_id: int,
        user_role: str,
        conversation_id: str,
        run_id: str,
    ) -> str:
        return f"agent:conversation:{self._scope(user_id, user_role, conversation_id)}:run:{run_id}"

    async def load_history(
        self,
        user_id: int,
        user_role: str,
        conversation_id: str | None,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        if not self._redis or not conversation_id:
            return []
        try:
            raw = await self._redis.get(self._history_key(user_id, user_role, conversation_id))
            if not raw:
                return []
            history = json.loads(raw)
            if not isinstance(history, list):
                return []
            return [
                {"role": item["role"], "content": item["content"]}
                for item in history[-limit:]
                if isinstance(item, dict)
                and item.get("role") in {"user", "assistant"}
                and isinstance(item.get("content"), str)
            ]
        except Exception as exc:
            logger.warning("Failed to load Agent history: %s", exc)
            return []

    async def persist_exchange(
        self,
        user_id: int,
        user_role: str,
        conversation_id: str | None,
        user_message: str,
        assistant_message: str,
        agent_id: str = "student.tutor",
    ) -> None:
        if not self._redis or not conversation_id:
            return
        try:
            key = self._history_key(user_id, user_role, conversation_id)
            history = await self.load_history(user_id, user_role, conversation_id, limit=100)
            history.append({"role": "user", "content": user_message})
            if assistant_message:
                history.append({"role": "assistant", "content": assistant_message})
            await self._redis.set(
                key,
                json.dumps(history[-40:], ensure_ascii=False),
                ex=self.ttl_seconds,
            )
            now = time.time()
            await self._redis.zadd(
                self._index_key(user_id, user_role),
                {conversation_id: now},
            )
            title = next(
                (
                    item["content"].strip()[:80]
                    for item in history
                    if item.get("role") == "user" and item.get("content", "").strip()
                ),
                "新对话",
            )
            await self._redis.hset(
                self._meta_key(user_id, user_role, conversation_id),
                mapping={
                    "title": title,
                    "agent_id": agent_id,
                    "message_count": str(len(history)),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self._redis.expire(
                self._meta_key(user_id, user_role, conversation_id),
                self.ttl_seconds,
            )
            await self._redis.expire(
                self._index_key(user_id, user_role),
                self.ttl_seconds,
            )
        except Exception as exc:
            logger.warning("Failed to persist Agent conversation: %s", exc)

    async def persist_run(
        self,
        user_id: int,
        user_role: str,
        conversation_id: str | None,
        run_id: str | None,
        agent_id: str,
        status: str,
        events: list[dict[str, Any]],
    ) -> None:
        if not self._redis or not conversation_id or not run_id:
            return
        try:
            record = {
                "run_id": run_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "user_role": user_role,
                "conversation_id": conversation_id,
                "status": status,
                "events": events[-250:],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._redis.set(
                self._run_key(user_id, user_role, conversation_id, run_id),
                json.dumps(record, ensure_ascii=False, default=str),
                ex=self.ttl_seconds,
            )
        except Exception as exc:
            logger.warning("Failed to persist Agent run: %s", exc)

    async def list_conversations(
        self,
        user_id: int,
        user_role: str,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        if not self._redis:
            return []
        try:
            limit = max(1, min(int(limit), 100))
            index_key = self._index_key(user_id, user_role)
            entries = await self._redis.zrevrange(index_key, 0, limit - 1, withscores=True)
            # Also scan legacy history keys so sessions created before the index
            # was introduced remain visible after a newer session exists.
            prefix = f"agent:conversation:{user_role}:{user_id}:"
            suffix = ":history"
            known_ids = {conversation_id for conversation_id, _ in entries}
            if len(entries) < limit:
                async for key in self._redis.scan_iter(match=f"{prefix}*{suffix}"):
                    conversation_id = key[len(prefix):-len(suffix)]
                    if conversation_id in known_ids:
                        continue
                    entries.append((conversation_id, 0.0))
                    known_ids.add(conversation_id)
                    if len(entries) >= limit:
                        break

            result = []
            for conversation_id, score in entries:
                history = await self.load_history(
                    user_id,
                    user_role,
                    conversation_id,
                    limit=100,
                )
                if not history:
                    continue
                meta = await self._redis.hgetall(
                    self._meta_key(user_id, user_role, conversation_id)
                )
                title = meta.get("title") or next(
                    (item["content"][:80] for item in history if item["role"] == "user"),
                    "新对话",
                )
                result.append({
                    "conversation_id": conversation_id,
                    "title": title,
                    "agent_id": meta.get("agent_id", "student.tutor"),
                    "message_count": len(history),
                    "last_message_at": meta.get("updated_at") or datetime.fromtimestamp(
                        float(score), timezone.utc
                    ).isoformat(),
                })
            return result
        except Exception as exc:
            logger.warning("Failed to list Agent conversations: %s", exc)
            return []

    async def get_conversation(
        self,
        user_id: int,
        user_role: str,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        if not self._redis:
            return None
        try:
            history = await self.load_history(user_id, user_role, conversation_id, limit=100)
            if not history:
                return None
            meta = await self._redis.hgetall(
                self._meta_key(user_id, user_role, conversation_id)
            )
            return {
                "conversation_id": conversation_id,
                "title": meta.get("title", "新对话"),
                "agent_id": meta.get("agent_id", "student.tutor"),
                "message_count": len(history),
                "messages": history,
                "last_message_at": meta.get("updated_at"),
            }
        except Exception as exc:
            logger.warning("Failed to load Agent conversation: %s", exc)
            return None

    async def delete_conversation(
        self,
        user_id: int,
        user_role: str,
        conversation_id: str,
    ) -> bool:
        if not self._redis:
            return False
        try:
            history_key = self._history_key(user_id, user_role, conversation_id)
            meta_key = self._meta_key(user_id, user_role, conversation_id)
            deleted = await self._redis.delete(history_key, meta_key)
            await self._redis.zrem(self._index_key(user_id, user_role), conversation_id)
            prefix = f"agent:conversation:{user_role}:{user_id}:{conversation_id}:run:"
            run_keys = [key async for key in self._redis.scan_iter(match=f"{prefix}*")]
            if run_keys:
                await self._redis.delete(*run_keys)
            return bool(deleted)
        except Exception as exc:
            logger.warning("Failed to delete Agent conversation: %s", exc)
            return False


agent_session_store = AgentSessionStore()
