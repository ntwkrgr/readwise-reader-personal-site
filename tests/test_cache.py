"""Tests for the persistent cache layer (Phases 1, 2, 4)."""
import time
import diskcache
import pytest
from unittest.mock import patch

import app as module


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path):
    """Replace the module-level _cache with a fresh temp cache for each test."""
    cache = diskcache.Cache(str(tmp_path / "cache"))
    with patch.object(module, "_cache", cache):
        yield cache
    cache.close()


# --- Version-based invalidation ---

def test_list_version_starts_at_zero():
    assert module._list_version() == 0


def test_invalidate_list_cache_increments_version():
    module.invalidate_list_cache()
    assert module._list_version() == 1
    module.invalidate_list_cache()
    assert module._list_version() == 2


def test_list_key_changes_after_invalidation():
    key_before = module._list_key("later", None, None)
    module.invalidate_list_cache()
    key_after = module._list_key("later", None, None)
    assert key_before != key_after
    assert "v0:" in key_before
    assert "v1:" in key_after


def test_list_key_encodes_all_params():
    key = module._list_key("later", "abc", "kindle")
    assert "later" in key
    assert "abc" in key
    assert "kindle" in key


# --- Request deduplication (_cached_fetch) ---

def test_cached_fetch_calls_fn_once_on_repeated_access():
    call_count = 0

    def fn():
        nonlocal call_count
        call_count += 1
        return {"value": 42}

    r1 = module._cached_fetch("key1", fn, ttl=60)
    r2 = module._cached_fetch("key1", fn, ttl=60)
    assert r1 == {"value": 42}
    assert r2 == {"value": 42}
    assert call_count == 1


def test_cached_fetch_calls_fn_again_after_ttl_expires():
    call_count = 0

    def fn():
        nonlocal call_count
        call_count += 1
        return {"v": call_count}

    module._cached_fetch("ttl_key", fn, ttl=1)
    time.sleep(1.1)
    module._cached_fetch("ttl_key", fn, ttl=1)
    assert call_count == 2


def test_cached_fetch_different_keys_fetch_independently():
    calls = []

    def fn_a():
        calls.append("a")
        return {"a": True}

    def fn_b():
        calls.append("b")
        return {"b": True}

    module._cached_fetch("key_a", fn_a, ttl=60)
    module._cached_fetch("key_b", fn_b, ttl=60)
    assert calls == ["a", "b"]


def test_cached_fetch_propagates_exception():
    def fn():
        raise module.ReadwiseAPIError("boom")

    with pytest.raises(module.ReadwiseAPIError, match="boom"):
        module._cached_fetch("err_key", fn, ttl=60)


def test_invalidate_article_cache_removes_entry():
    module._cache.set(module._article_key("doc1"), {"title": "hi"}, expire=60)
    module.invalidate_article_cache("doc1")
    assert module._cache.get(module._article_key("doc1"), default=module._MISSING) is module._MISSING


# --- Refresh cooldown ---

def test_can_refresh_true_when_never_refreshed():
    assert module._can_refresh() is True


def test_can_refresh_false_immediately_after_mark():
    module._mark_refresh()
    assert module._can_refresh() is False


def test_can_refresh_true_after_cooldown_elapsed():
    module._cache.set("last_refresh", time.time() - module.REFRESH_COOLDOWN - 1)
    assert module._can_refresh() is True


def test_cache_age_seconds_none_when_never_refreshed():
    assert module.cache_age_seconds() is None


def test_cache_age_seconds_approx_zero_just_after_mark():
    module._mark_refresh()
    age = module.cache_age_seconds()
    assert age is not None
    assert 0 <= age <= 2
