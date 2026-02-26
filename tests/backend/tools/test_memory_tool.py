from backend.core.session_memory import SessionMemoryStore
from backend.tools import memory_tool


def test_memory_tool_remember_recall_forget(tmp_path, monkeypatch):
    store = SessionMemoryStore(path=tmp_path / "session_memory.json")
    monkeypatch.setattr(memory_tool, "_STORE", store)

    saved = memory_tool.remember_memory("favorite_color", "green", chat_id="chat-1")
    recalled = memory_tool.recall_memory("favorite_color", chat_id="chat-1")
    deleted = memory_tool.forget_memory("favorite_color", chat_id="chat-1")
    missing = memory_tool.recall_memory("favorite_color", chat_id="chat-1")

    assert "Saved memory" in saved
    assert "favorite_color: green" in recalled
    assert "Deleted memory" in deleted
    assert "No memory found" in missing


def test_memory_tool_tasks(tmp_path, monkeypatch):
    store = SessionMemoryStore(path=tmp_path / "session_memory.json")
    monkeypatch.setattr(memory_tool, "_STORE", store)

    added = memory_tool.add_task_memory("prepare demo", chat_id="chat-2")
    listed = memory_tool.list_task_memory(chat_id="chat-2")
    completed = memory_tool.complete_task_memory("prepare demo", chat_id="chat-2")
    listed_after = memory_tool.list_task_memory(chat_id="chat-2")

    assert "Added task" in added
    assert "prepare demo" in listed
    assert "Completed task" in completed
    assert "No active tasks" in listed_after
