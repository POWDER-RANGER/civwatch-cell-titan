"""Simple asyncio broadcast hub for live telemetry events."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Set


class LiveHub:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue] = []
        payload = json.dumps(event, default=str)
        for q in list(self._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.discard(q)

    @property
    def listener_count(self) -> int:
        return len(self._subscribers)


hub = LiveHub()
