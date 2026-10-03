"""Cache evidence verify() against tip so /api/health is not O(n) every request."""
from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_cached: dict[str, Any] | None = None
_tip_key: tuple[int, str] | None = None
_cached_at = 0.0
_TTL = 2.0


def cached_verify(chain) -> dict[str, Any]:
    global _cached, _tip_key, _cached_at
    tip = chain.tip_snapshot()
    key = (int(tip.get("seq") or 0), str(tip.get("last_hash") or ""))
    now = time.monotonic()
    with _lock:
        if _cached is not None and _tip_key == key and (now - _cached_at) < _TTL:
            return dict(_cached)
    result = chain.verify()
    with _lock:
        _cached = dict(result)
        _tip_key = key
        _cached_at = now
    return result
