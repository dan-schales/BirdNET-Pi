import unittest
from datetime import date

from scripts.utils.predictions import (
    compute_predictions,
    classify_status,
    _is_in_active_window,
    _circular_distance_forward,
)


def _wk(sci, com, year, week, count):
    return {"sci_name": sci, "com_name": com, "year": year, "week": week, "count": count}


def _meta(sci, total, first_ever, last_seen, first_this_year=None):
    return {"sci_name": sci, "total_count": total, "first_ever": first_ever,
            "last_seen": last_seen, "first_this_year": first_this_year}


class TestActiveWindow(unittest.TestCase):
    def test_normal_window(self):
        # Spring/summer species: arrival wk 12, departure wk 30
        self.assertTrue(_is_in_active_window(15, 12, 30))
        self.assertTrue(_is_in_active_window(11, 12, 30))   # within tolerance
        self.assertFalse(_is_in_active_window(40, 12, 30))

    def test_wraparound_window(self):
        # Winter species: arrival wk 48, departure wk 8
        self.assertTrue(_is_in_active_window(50, 48, 8))
        self.assertTrue(_is_in_active_window(2, 48, 8))
        self.assertFalse(_is_in_active_window(20, 48, 8))


class TestCircularDistance(unittest.TestCase):
    def test_forward(self):
        self.assertEqual(_circular_distance_forward(10, 14), 4)
        self.assertEqual(_circular_distance_forward(50, 2), 5)  # wrap
        self.assertEqual(_circular_distance_forward(10, 10), 0)


class TestClassifyStatus(unittest.TestCase):
    def test_present_when_recent(self):
        s = classify_status(arrival_week=10, departure_week=30, current_week=20,
                            days_since_last_seen=3, years_observed=3,
                            weeks_observed_count=15)
        self.assertEqual(s, "present")

    def test_expected_now_in_window_not_seen(self):
        s = classify_status(arrival_week=10, departure_week=30, current_week=15,
                            days_since_last_seen=120, years_observed=3,
                            weeks_observed_count=12)
        self.assertEqual(s, "expected_now")

    def test_coming_soon_before_arrival(self):
        s = classify_status(arrival_week=20, departure_week=35, current_week=17,
                            days_since_last_seen=300, years_observed=3,
                            weeks_observed_count=10)
        self.assertEqual(s, "coming_soon")

    def test_out_of_season_far_off(self):
        s = classify_status(arrival_week=20, departure_week=35, current_week=45,
                            days_since_last_seen=200, years_observed=3,
                            weeks_observed_count=10)
        self.assertEqual(s, "out_of_season")

    def test_late_season_in_window_recent(self):
        s = classify_status(arrival_week=10, departure_week=30, current_week=29,
                            days_since_last_seen=20, years_observed=3,
                            weeks_observed_count=12)
        self.assertEqual(s, "late_season")

    def test_year_round_overdue_when_silent(self):
        s = classify_status(arrival_week=0, departure_week=52, current_week=20,
                            days_since_last_seen=60, years_observed=3,
                            weeks_observed_count=45)
        self.assertEqual(s, "overdue")

    def test_insufficient_when_no_arrival(self):
        s = classify_status(arrival_week=None, departure_week=None, current_week=20,
                            days_since_last_seen=None, years_observed=0,
                            weeks_observed_count=0)
        self.assertEqual(s, "insufficient_data")


class TestComputePredictions(unittest.TestCase):
    def test_filters_below_min_detections(self):
        rows = [_wk("Aaa bbb", "A", 2024, 10, 1)]
        meta = [_meta("Aaa bbb", 1, "2024-03-01", "2024-03-01 09:00:00")]
        out = compute_predictions(rows, meta, today=date(2024, 5, 1), min_detections=3)
        self.assertEqual(out["species"], [])

    def test_year_in_data_count(self):
        rows = [
            _wk("X x", "X", 2022, 5, 5),
            _wk("X x", "X", 2023, 5, 5),
            _wk("X x", "X", 2024, 5, 5),
        ]
        meta = [_meta("X x", 15, "2022-02-01", "2024-02-05 08:00:00", "2024-02-05")]
        out = compute_predictions(rows, meta, today=date(2024, 6, 1), min_detections=1)
        self.assertEqual(out["years_in_data"], 3)
        sp = out["species"][0]
        self.assertEqual(sp["years_observed"], 3)
        self.assertEqual(sp["arrival_week"], 5)
        self.assertEqual(sp["peak_week"], 5)
        self.assertEqual(sp["frequency_by_week"][5], 1.0)
        self.assertEqual(sp["frequency_by_week"][10], 0.0)

    def test_arrival_is_median_of_yearly_first_weeks(self):
        rows = [
            _wk("Y y", "Y", 2022, 8,  3),
            _wk("Y y", "Y", 2022, 18, 5),
            _wk("Y y", "Y", 2023, 12, 3),
            _wk("Y y", "Y", 2023, 20, 5),
            _wk("Y y", "Y", 2024, 14, 3),
            _wk("Y y", "Y", 2024, 22, 5),
        ]
        meta = [_meta("Y y", 24, "2022-02-20", "2024-05-30 08:00:00", "2024-04-01")]
        out = compute_predictions(rows, meta, today=date(2024, 5, 1), min_detections=1)
        sp = out["species"][0]
        # First weeks per year: 8, 12, 14 → median 12
        self.assertEqual(sp["arrival_week"], 12)
        self.assertEqual(sp["departure_week"], 20)

    def test_status_uses_today(self):
        # Species observed in weeks 20-30 across 2 years; current week is mid-window,
        # last seen 100 days ago → should be expected_now.
        rows = [
            _wk("Z z", "Z", 2023, 22, 5),
            _wk("Z z", "Z", 2023, 28, 5),
            _wk("Z z", "Z", 2024, 22, 5),
            _wk("Z z", "Z", 2024, 28, 5),
        ]
        # today = 2025-06-01 → strftime('%W') ~ week 22 in a Monday-start system
        meta = [_meta("Z z", 20, "2023-05-30", "2024-07-15 08:00:00", None)]
        out = compute_predictions(rows, meta, today=date(2025, 6, 1), min_detections=1)
        sp = out["species"][0]
        self.assertIn(sp["status"], ("expected_now", "overdue", "late_season"))
        # not detected in current calendar year → not detected_this_year
        self.assertFalse(sp["detected_this_year"])


if __name__ == "__main__":
    unittest.main()
