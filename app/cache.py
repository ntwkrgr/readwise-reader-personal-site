import os
import time

from typing import Any

import diskcache

_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
CACHE_DIR = os.environ.get("CACHE_DIR", os.path.join(_APP_DIR, ".cache"))
LIST_CACHE_TTL = int(os.environ.get("LIST_CACHE_TTL", 1200))   # 20 minutes
ARTICLE_CACHE_TTL = int(os.environ.get("ARTICLE_CACHE_TTL", 3600))  # 60 minutes
REFRESH_COOLDOWN = 120  # 2 minutes

_MISSING = object()
_cache = diskcache.Cache(CACHE_DIR)


def _list_version() -> int:
    return _cache.get("list_version", default=0)


def _list_key(location: str, page_cursor: str | None, tag: str | None) -> str:
    return f"list:v{_list_version()}:{location}:{page_cursor or ''}:{tag or ''}"


def _article_key(doc_id: str) -> str:
    return f"article:{doc_id}"


def cached_fetch(key: str, fetch_fn, ttl: int) -> Any:
    """Double-checked lock: check -> lock -> check -> fetch -> store.

    expire=30 on the Lock auto-releases it if the holder dies mid-operation,
    preventing permanent deadlocks across gunicorn workers.
    """
    result = _cache.get(key, default=_MISSING)
    if result is not _MISSING:
        return result
    with diskcache.Lock(_cache, f"lock:{key}", expire=30):
        result = _cache.get(key, default=_MISSING)
        if result is not _MISSING:
            return result
        result = fetch_fn()
        _cache.set(key, result, expire=ttl)
        return result


def invalidate_list_cache() -> None:
    _cache.incr("list_version", default=0)


def invalidate_article_cache(doc_id: str) -> None:
    _cache.delete(_article_key(doc_id))


def can_refresh() -> bool:
    last = _cache.get("last_refresh")
    return last is None or (time.time() - last) >= REFRESH_COOLDOWN


def mark_refresh() -> None:
    _cache.set("last_refresh", time.time())


def cache_age_seconds() -> int | None:
    last = _cache.get("last_refresh")
    return int(time.time() - last) if last is not None else None
