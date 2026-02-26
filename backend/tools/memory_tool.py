"""
Memory tools for persistent session context.
"""

from backend.core.session_memory import SessionMemoryStore

_STORE = SessionMemoryStore()


def remember_memory(key: str, value: str, chat_id: str = "default") -> str:
    """
    Save a persistent memory item for this chat/session.

    key: memory key such as "favorite_coffee" or "project_name"
    value: memory value to store
    chat_id: optional session id; defaults to "default"
    """
    try:
        _STORE.remember_fact(chat_id=chat_id, key=key, value=value)
    except ValueError as exc:
        return f"Could not save memory: {exc}"
    return f"Saved memory '{key.strip()}'."


def recall_memory(key: str = "", chat_id: str = "default") -> str:
    """
    Read memory items for this chat/session.

    key: optional memory key. If omitted, returns all memory items.
    chat_id: optional session id; defaults to "default"
    """
    facts = _STORE.recall_facts(chat_id=chat_id, key=key)
    if not facts:
        if key.strip():
            return f"No memory found for '{key.strip()}'."
        return "No saved memory yet."

    lines = [f"- {k}: {v}" for k, v in sorted(facts.items())]
    return "Saved memory:\n" + "\n".join(lines)


def forget_memory(key: str, chat_id: str = "default") -> str:
    """
    Delete a memory item for this chat/session.

    key: memory key to delete
    chat_id: optional session id; defaults to "default"
    """
    try:
        removed = _STORE.forget_fact(chat_id=chat_id, key=key)
    except ValueError as exc:
        return f"Could not delete memory: {exc}"

    if removed:
        return f"Deleted memory '{key.strip()}'."
    return f"No memory found for '{key.strip()}'."


def add_task_memory(task: str, chat_id: str = "default") -> str:
    """
    Add a task to active task memory.

    task: short task description
    chat_id: optional session id; defaults to "default"
    """
    try:
        _STORE.add_task(chat_id=chat_id, task=task)
    except ValueError as exc:
        return f"Could not add task: {exc}"
    return f"Added task '{task.strip()}'."


def list_task_memory(chat_id: str = "default") -> str:
    """
    List active tasks stored in memory for this chat/session.

    chat_id: optional session id; defaults to "default"
    """
    tasks = _STORE.list_tasks(chat_id=chat_id)
    if not tasks:
        return "No active tasks saved."
    lines = [f"{idx + 1}. {task}" for idx, task in enumerate(tasks)]
    return "Active tasks:\n" + "\n".join(lines)


def complete_task_memory(task: str, chat_id: str = "default") -> str:
    """
    Mark a saved task as complete and remove it from active memory.

    task: exact task text to mark complete
    chat_id: optional session id; defaults to "default"
    """
    try:
        removed = _STORE.complete_task(chat_id=chat_id, task=task)
    except ValueError as exc:
        return f"Could not complete task: {exc}"

    if removed:
        return f"Completed task '{task.strip()}'."
    return f"Task not found: '{task.strip()}'."
