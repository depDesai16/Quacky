"""Memory list/forget tool wrappers for Quacky."""

from backend.core.memory_store import (
    clear_all_memory,
    clear_preferences,
    clear_task_notes,
    forget_preference,
    forget_task_note,
    get_preferences,
    get_task_notes,
)


def list_memory(scope: str = "all") -> str:
    """
    List remembered preferences and/or task notes.
    scope: "all", "preferences", or "tasks".
    """
    s = (scope or "all").strip().lower()
    if s in {"prefs", "pref", "preference"}:
        s = "preferences"
    elif s in {"task", "todo", "notes"}:
        s = "tasks"
    elif s not in {"all", "preferences", "tasks"}:
        return "Invalid memory scope. Use 'all', 'preferences', or 'tasks'."

    prefs = get_preferences(limit=25) if s in {"all", "preferences"} else []
    tasks = get_task_notes(limit=25) if s in {"all", "tasks"} else []

    lines: list[str] = []
    if s in {"all", "preferences"}:
        if prefs:
            lines.append("Remembered preferences:")
            for idx, value in enumerate(prefs, start=1):
                lines.append(f"- [{idx}] {value}")
        else:
            lines.append("Remembered preferences: none.")

    if s in {"all", "tasks"}:
        if tasks:
            lines.append("Remembered task notes:")
            for idx, value in enumerate(tasks, start=1):
                lines.append(f"- [{idx}] {value}")
        else:
            lines.append("Remembered task notes: none.")

    return "\n".join(lines)


def forget_memory_item(scope: str, value: str) -> str:
    """
    Forget one remembered preference or task note.
    scope: "preferences" | "tasks"
    """
    s = (scope or "").strip().lower()
    v = (value or "").strip()
    if not v:
        return "Please provide the exact preference/task text to forget."

    if s in {"preferences", "preference", "pref", "prefs"}:
        removed = forget_preference(v)
        return (
            f"Forgot preference matching '{v}'."
            if removed
            else f"No remembered preference matched '{v}'."
        )

    if s in {"tasks", "task", "todo", "note", "notes"}:
        removed = forget_task_note(v)
        return (
            f"Forgot task note matching '{v}'."
            if removed
            else f"No remembered task note matched '{v}'."
        )

    return "Invalid memory scope. Use 'preferences' or 'tasks'."


def clear_memory(scope: str = "all") -> str:
    """
    Clear remembered preferences/task notes in bulk.
    scope: "all", "preferences", or "tasks".
    """
    s = (scope or "all").strip().lower()
    if s in {"prefs", "pref", "preference"}:
        s = "preferences"
    elif s in {"task", "todo", "notes"}:
        s = "tasks"
    elif s not in {"all", "preferences", "tasks"}:
        return "Invalid memory scope. Use 'all', 'preferences', or 'tasks'."

    if s == "preferences":
        count = clear_preferences()
        return f"Cleared {count} remembered preferences."

    if s == "tasks":
        count = clear_task_notes()
        return f"Cleared {count} remembered task notes."

    pref_count, task_count = clear_all_memory()
    return (
        "Cleared all remembered memory: "
        f"{pref_count} preferences and {task_count} task notes."
    )
