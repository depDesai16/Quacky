import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core import memory_store


class MemoryStoreTests(unittest.TestCase):
    def test_update_preference_rewrites_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "user_memory.json"
            with patch.object(memory_store, "_FILE", memory_path):
                memory_store.add_preference("concise responses")
                updated = memory_store.update_preference("concise responses", "short responses")

                self.assertTrue(updated)
                self.assertEqual(memory_store.get_preferences(limit=5), ["short responses"])

    def test_get_task_notes_data_returns_structured_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "user_memory.json"
            with patch.object(memory_store, "_FILE", memory_path):
                memory_store.add_task_note("submit payroll")
                items = memory_store.get_task_notes_data(limit=5)

                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["value"], "submit payroll")
                self.assertIn("updated_at", items[0])


if __name__ == "__main__":
    unittest.main()
