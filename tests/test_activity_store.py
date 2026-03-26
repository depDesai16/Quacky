import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core import activity_store


class ActivityStoreTests(unittest.TestCase):
    def test_add_calendar_event_normalizes_fields_and_lists_most_recent_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "activity_log.json"

            with patch.object(activity_store, "_FILE", file_path):
                activity_store.add_calendar_event(
                    action="  CREATE  ",
                    title="  Team   Sync  ",
                    location=" Room   12 ",
                    details=" Weekly   update ",
                    result=" created   ok ",
                )
                activity_store.add_calendar_event(
                    action="delete",
                    title="Old event",
                    status=" error ",
                )

                events = activity_store.list_calendar_events(limit=10)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["action"], "delete")
        self.assertEqual(events[0]["status"], "error")
        self.assertEqual(events[1]["action"], "create")
        self.assertEqual(events[1]["title"], "Team Sync")
        self.assertEqual(events[1]["location"], "Room 12")
        self.assertEqual(events[1]["details"], "Weekly update")
        self.assertEqual(events[1]["result"], "created ok")

    def test_add_calendar_event_respects_max_event_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "activity_log.json"

            with patch.object(activity_store, "_FILE", file_path):
                with patch.object(activity_store, "_MAX_EVENTS", 2):
                    activity_store.add_calendar_event(action="create", title="One")
                    activity_store.add_calendar_event(action="create", title="Two")
                    activity_store.add_calendar_event(action="create", title="Three")

                    events = activity_store.list_calendar_events(limit=10)

        self.assertEqual([event["title"] for event in events], ["Three", "Two"])

    def test_list_calendar_events_ignores_invalid_file_contents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "activity_log.json"
            file_path.write_text('{"calendar_events": ["bad-entry"]}', encoding="utf-8")

            with patch.object(activity_store, "_FILE", file_path):
                events = activity_store.list_calendar_events(limit=10)

        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
