from backend.core.session_memory import SessionMemoryStore


def test_session_memory_round_trip(tmp_path):
    store = SessionMemoryStore(path=tmp_path / "session_memory.json")

    session = store.get_session("chat-a")
    assert session["facts"] == {}
    assert session["active_tasks"] == []

    store.remember_fact("chat-a", "favorite_ide", "cursor")
    store.add_task("chat-a", "finish sprint review")
    store.save_session(
        "chat-a",
        {
            "last_topic": "calendar",
            "pending_action": {"kind": "calendar", "op": "create"},
            "facts": {"favorite_ide": "cursor"},
            "active_tasks": ["finish sprint review"],
        },
    )

    loaded = store.get_session("chat-a")
    assert loaded["last_topic"] == "calendar"
    assert loaded["pending_action"]["op"] == "create"
    assert loaded["facts"]["favorite_ide"] == "cursor"
    assert loaded["active_tasks"] == ["finish sprint review"]


def test_session_memory_fact_delete_and_task_complete(tmp_path):
    store = SessionMemoryStore(path=tmp_path / "session_memory.json")
    store.remember_fact("chat-b", "timezone", "PST")
    store.add_task("chat-b", "book flights")

    assert store.forget_fact("chat-b", "timezone") is True
    assert store.recall_facts("chat-b", "timezone") == {}
    assert store.complete_task("chat-b", "book flights") is True
    assert store.list_tasks("chat-b") == []
