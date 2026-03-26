import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.features.timers import timer_feature


class TimerFeatureTests(unittest.TestCase):
    def test_set_timer_rejects_invalid_durations(self):
        self.assertIn("greater than zero", timer_feature.set_timer(0))
        self.assertIn("too long", timer_feature.set_timer(timer_feature._MAX_TIMER_SECONDS + 1))

    def test_set_timer_and_cancel_by_label(self):
        fresh_manager = timer_feature._TimerManager()
        with patch.object(timer_feature, "_MANAGER", fresh_manager):
            created = timer_feature.set_timer(60, label="tea")
            listed = timer_feature.list_timers()
            canceled = timer_feature.cancel_timer("tea")

        self.assertIn("Set timer TMR-0001 (tea).", created)
        self.assertIn("Timer TMR-0001 (tea):", listed)
        self.assertIn("Canceled Timer TMR-0001 (tea).", canceled)

    def test_set_alarm_accepts_absolute_datetime_text(self):
        fresh_manager = timer_feature._TimerManager()
        with patch.object(timer_feature, "_MANAGER", fresh_manager):
            result = timer_feature.set_alarm("2030-01-02 09:15", label="gym")

        self.assertIn("Set alarm TMR-0001 (gym) for 2030-01-02 09:15:00 AM.", result)

    def test_drain_due_alerts_only_returns_each_alert_once(self):
        fresh_manager = timer_feature._TimerManager()
        with patch.object(timer_feature, "_MANAGER", fresh_manager):
            entry = fresh_manager.create_timer(10, label="stretch")
            entry.trigger_at = datetime.now() - timedelta(seconds=1)

            first = timer_feature.drain_due_alerts()
            second = timer_feature.drain_due_alerts()

        self.assertEqual(first, ["Timer TMR-0001 (stretch) is due now."])
        self.assertEqual(second, [])

    def test_get_active_timers_data_returns_structured_entries(self):
        fresh_manager = timer_feature._TimerManager()
        with patch.object(timer_feature, "_MANAGER", fresh_manager):
            fresh_manager.create_timer(90, label="focus")
            items = timer_feature.get_active_timers_data()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["timer_id"], "TMR-0001")
        self.assertEqual(items[0]["kind"], "timer")
        self.assertEqual(items[0]["label"], "focus")
        self.assertGreaterEqual(items[0]["remaining_seconds"], 1)


if __name__ == "__main__":
    unittest.main()
