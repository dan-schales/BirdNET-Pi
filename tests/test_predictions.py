import unittest
from datetime import date

from scripts.utils.predictions import (
    compute_predictions,
    classify_status,
    _is_in_active_window,
    _circular_distance_forward,
    _next_active_week_offset,
    WEEKS_PER_YEAR,
)


def _wk(sci, com, year, week, count):
    return {"sci_name": sci, "com_name": com, "year": year, "week": week, "count": count}


def _meta(sci, total, first_ever, last_seen, first_this_year=None):
    return {"sci_name": sci, "total_count": total, "first_ever": first_ever,
            "last_seen": last_seen, "first_this_year": first_this_year}


def _freq(active_weeks, n=WEEKS_PER_YEAR, value=0.5):
    """Build a frequency_by_week array with `value` at the specified weeks."""
    arr = [0.0] * n
    for w in active_weeks:
        arr[w] = value
    return arr


class TestActiveWindow(unittest.TestCase):
    def test_normal_window(self):
        self.assertTrue(_is_in_active_window(15, 12, 30))
        self.assertTrue(_is_in_active_window(11, 12, 30))
        self.assertFalse(_is_in_active_window(40, 12, 30))

    def test_wraparound_window(self):
        self.assertTrue(_is_in_active_window(50, 48, 8))
        self.assertTrue(_is_in_active_window(2, 48, 8))
        self.assertFalse(_is_in_active_window(20, 48, 8))


class TestCircularDistance(unittest.TestCase):
    def test_forward(self):
        self.assertEqual(_circular_distance_forward(10, 14), 4)
        self.assertEqual(_circular_distance_forward(50, 2), 5)
        self.assertEqual(_circular_distance_forward(10, 10), 0)


class TestNextActiveOffset(unittest.TestCase):
    def test_finds_next_week(self):
        freq = _freq([20, 25])
        self.assertEqual(_next_active_week_offset(freq, 18), 2)
        self.assertEqual(_next_active_week_offset(freq, 22), 3)

    def test_wraps_around_year(self):
        freq = _freq([2])
        self.assertEqual(_next_active_week_offset(freq, 50), 5)

    def test_returns_none_beyond_lookahead(self):
        freq = _freq([2])
        self.assertIsNone(_next_active_week_offset(freq, 30, max_lookahead=4))


class TestClassifyStatus(unittest.TestCase):
    def test_present_when_recent(self):
        s = classify_status(
            frequency_by_week=_freq([10, 12, 14, 16, 18, 20]),
            current_week=18, days_since_last_seen=3,
            years_observed=3, weeks_observed_count=6, detected_this_year=True)
        self.assertEqual(s, "present")

    def test_expected_now_uses_actual_history(self):
        # Detected at week 16-20 historically, current week 18 → expected now
        s = classify_status(
            frequency_by_week=_freq([16, 18, 20]),
            current_week=18, days_since_last_seen=120,
            years_observed=3, weeks_observed_count=3, detected_this_year=False)
        self.assertEqual(s, "expected_now")

    def test_single_distant_detection_not_expected_now(self):
        # Only one historical detection at week 16, current week 18 (2 weeks away).
        # With the tightened classifier this should NOT be 'expected_now' because
        # the single hit isn't in the immediate +/-1 window and there's no
        # second hit anywhere in the +/-2 window.
        s = classify_status(
            frequency_by_week=_freq([16]),
            current_week=18, days_since_last_seen=120,
            years_observed=2, weeks_observed_count=1, detected_this_year=False)
        self.assertNotEqual(s, "expected_now")

    def test_two_sporadic_detections_within_2wk_window_expected(self):
        # Two non-adjacent hits in the +/-2 window count as enough evidence.
        s = classify_status(
            frequency_by_week=_freq([16, 20]),
            current_week=18, days_since_last_seen=120,
            years_observed=2, weeks_observed_count=2, detected_this_year=False)
        self.assertEqual(s, "expected_now")

    def test_NOT_expected_now_in_empty_gap(self):
        # Detected at weeks 4 and 30 only; current week 18 is in a gap.
        # Old logic would say expected_now (window 4-30 spans it). New logic
        # correctly classifies as coming_soon (next cluster is week 30).
        s = classify_status(
            frequency_by_week=_freq([2, 4, 28, 30]),
            current_week=18, days_since_last_seen=120,
            years_observed=3, weeks_observed_count=4, detected_this_year=False)
        self.assertNotEqual(s, "expected_now")
        self.assertIn(s, ("coming_soon", "out_of_season"))

    def test_coming_soon_within_8_weeks(self):
        s = classify_status(
            frequency_by_week=_freq([24]),
            current_week=18, days_since_last_seen=200,
            years_observed=3, weeks_observed_count=1, detected_this_year=False)
        self.assertEqual(s, "coming_soon")

    def test_late_season_when_recent_in_window(self):
        s = classify_status(
            frequency_by_week=_freq([16, 18, 20]),
            current_week=18, days_since_last_seen=20,
            years_observed=3, weeks_observed_count=3, detected_this_year=True)
        self.assertEqual(s, "late_season")

    def test_overdue_when_past_active_no_detection_this_year(self):
        # Active in weeks 13-15, current week 18, never seen this year
        s = classify_status(
            frequency_by_week=_freq([13, 14, 15]),
            current_week=18, days_since_last_seen=200,
            years_observed=3, weeks_observed_count=3, detected_this_year=False)
        self.assertEqual(s, "overdue")

    def test_out_of_season_far_off(self):
        s = classify_status(
            frequency_by_week=_freq([45]),
            current_week=18, days_since_last_seen=200,
            years_observed=3, weeks_observed_count=1, detected_this_year=False)
        self.assertEqual(s, "out_of_season")

    def test_year_round_overdue_when_silent(self):
        freq = [0.5] * WEEKS_PER_YEAR
        s = classify_status(
            frequency_by_week=freq,
            current_week=20, days_since_last_seen=60,
            years_observed=3, weeks_observed_count=45, detected_this_year=True)
        self.assertEqual(s, "overdue")

    def test_insufficient_when_no_history(self):
        s = classify_status(
            frequency_by_week=[0.0] * WEEKS_PER_YEAR,
            current_week=20, days_since_last_seen=None,
            years_observed=0, weeks_observed_count=0, detected_this_year=False)
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
        self.assertEqual(sp["arrival_week"], 12)
        self.assertEqual(sp["departure_week"], 20)

    def test_sparse_species_with_gaps_not_expected_in_gap(self):
        # Mimics Herring Gull case: detections clustered in early weeks and
        # late weeks, gap in late spring. Current week sits in the gap.
        rows = []
        for y in (2024, 2025):
            for w in (2, 4, 30, 32, 50, 52):
                rows.append(_wk("Larus argentatus", "Herring Gull", y, w, 1))
        meta = [_meta("Larus argentatus", 12, "2024-01-15",
                      "2026-02-18 08:00:00", None)]
        out = compute_predictions(rows, meta, today=date(2026, 5, 6), min_detections=1)
        sp = out["species"][0]
        self.assertNotEqual(sp["status"], "expected_now",
                            "should not be 'expected_now' when current week is in a historical gap")
        self.assertIn(sp["status"], ("coming_soon", "out_of_season"))


if __name__ == "__main__":
    unittest.main()
