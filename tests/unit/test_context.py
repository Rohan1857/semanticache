from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from semanticache import clear_context, context, get_context, set_context
from semanticache.adapters.redis.store import RedisVectorStore

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_BODY = b'{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

def test_context_manager_basic():
    """Test that the context manager sets and unsets variables correctly."""
    assert get_context() is None
    with context(tenant_id="user1", app="test"):
        ctx = get_context()
        assert ctx is not None
        assert ctx["tenant_id"] == "user1"
        assert ctx["app"] == "test"
    assert get_context() is None

def test_set_clear_context():
    """Test manual context setting and clearing."""
    assert get_context() is None
    set_context(org="acme")
    ctx = get_context()
    assert ctx is not None
    assert ctx["org"] == "acme"
    clear_context()
    assert get_context() is None

def test_engine_uses_metadata_in_key(make_engine):
    """Test that metadata affects the generated cache key."""
    engine = make_engine()
    req = httpx.Request("POST", OPENAI_URL, content=OPENAI_BODY)
    prepared = engine.prepare(req)

    assert prepared is not None

    key1 = engine._make_key(f"{prepared.scope}:{prepared.prompt}", metadata=None)
    key2 = engine._make_key(f"{prepared.scope}:{prepared.prompt}", metadata={"tenant": "1"})
    key3 = engine._make_key(f"{prepared.scope}:{prepared.prompt}", metadata={"tenant": "2"})
    key4 = engine._make_key(f"{prepared.scope}:{prepared.prompt}", metadata={"tenant": "1"})

    assert key1 != key2
    assert key2 != key3
    assert key2 == key4  # Deterministic

def test_engine_passes_metadata_to_store(make_engine, openai_chat_response):
    """Test that the engine propagates context to the VectorStore."""
    engine = make_engine()
    # Spy on the memory store
    store = engine._store
    store.search = MagicMock(return_value=None)
    store.store = MagicMock()

    req = httpx.Request("POST", OPENAI_URL, content=OPENAI_BODY)
    prepared = engine.prepare(req)
    assert prepared is not None

    with context(tenant="xyz"):
        engine.lookup(prepared)
        # Search should receive metadata
        store.search.assert_called_once()
        assert store.search.call_args.kwargs.get("metadata") == {"tenant": "xyz"}

        engine.store(prepared, openai_chat_response)
        # Store should receive metadata
        store.store.assert_called_once()
        assert store.store.call_args.kwargs.get("metadata") == {"tenant": "xyz"}

def test_redis_store_vsim_vadd_args():
    """Test that RedisVectorStore correctly formats TAGS arguments."""
    store = RedisVectorStore("redis://localhost:6379")
    mock_client = MagicMock()
    mock_pipe = MagicMock()
    mock_client.pipeline.return_value = mock_pipe
    store._get_client = MagicMock(return_value=mock_client)

    # Test search (VSIM)
    store.search("scope", [0.1, 0.2], 0.9, metadata={"tenant": "a", "user": "b"})

    mock_client.execute_command.assert_called_once()
    args = mock_client.execute_command.call_args.args
    assert args[0] == "VSIM"
    assert "TAGS" in args
    assert "tenant" in args
    assert "a" in args
    assert "user" in args
    assert "b" in args
    assert args[-3:] == ("WITHSCORES", "COUNT", 1)

    # Test store (VADD)
    store.store("scope", "key", [0.1, 0.2], b"data", metadata={"tenant": "a"})

    mock_pipe.execute_command.assert_called_once()
    args = mock_pipe.execute_command.call_args.args
    assert args[0] == "VADD"
    assert args[-3:] == ("TAGS", "tenant", "a")
