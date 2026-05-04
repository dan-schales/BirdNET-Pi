"""Seasonal arrival/peak predictions derived from local detection history.

The aggregation works entirely from rows shaped like:
    {"sci_name": str, "com_name": str, "year": int, "week": int, "count": int}

Plus a list of per-species metadata rows:
    {"sci_name": str, "total_count": int, "first_ever": "YYYY-MM-DD",
     "last_seen": "YYYY-MM-DD HH:MM:SS", "first_this_year": "YYYY-MM-DD" | None}

This module only computes statistics; it does not touch the database. The
caller (api_server) supplies query results so the logic can be tested with
fixture data.
"""

from datetime import date, datetime
from statistics import median


WEEKS_PER_YEAR = 53  # SQLite strftime('%W') yields 00-53


def _safe_median(values):
    return int(round(median(values))) if values else None


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _days_between(d1, d2):
    if d1 is None or d2 is None:
        return None
    return (d2 - d1).days


def _circular_distance_forward(from_week, to_week):
    """Number of weeks from `from_week` to `to_week` walking forward in time."""
    return (to_week - from_week) % WEEKS_PER_YEAR


def classify_status(frequency_by_week, current_week, days_since_last_seen,
                    years_observed, weeks_observed_count, detected_this_year):
    """Determine the species' current seasonal status from its weekly history.

    Classification is driven entirely by `frequency_by_week` (the per-week
    fraction of years in which the species was detected). This avoids the
    "continuous active window" trap where a species detected only in spring
    and fall would be flagged as expected during the empty summer gap.

    Returns one of: 'present', 'expected_now', 'coming_soon', 'overdue',
    'late_season', 'out_of_season', 'insufficient_data'.
    """
    n = len(frequency_by_week)
    if years_observed < 1 or not any(frequency_by_week):
        return "insufficient_data"

    if days_since_last_seen is not None and days_since_last_seen <= 14:
        return "present"

    # Year-round residents (detected in 40+ distinct weeks across history)
    if weeks_observed_count >= 40:
        return "overdue" if years_observed >= 2 else "present"

    def has_freq_within(center, half_window):
        return any(frequency_by_week[(center + o) % n] > 0
                   for o in range(-half_window, half_window + 1))

    # Historically detected at or near the current week (±2)
    if has_freq_within(current_week, 2):
        if days_since_last_seen is not None and days_since_last_seen <= 30:
            return "late_season"
        return "expected_now" if years_observed >= 2 else "out_of_season"

    # Look forward up to 8 weeks for the next historical detection cluster
    for i in range(3, 9):
        w = (current_week + i) % n
        if frequency_by_week[w] > 0:
            return "coming_soon"

    # Recent past had detections but the species hasn't shown this year
    if not detected_this_year:
        for i in range(3, 7):
            w = (current_week - i) % n
            if frequency_by_week[w] > 0:
                return "overdue"

    return "out_of_season"


def _next_active_week_offset(frequency_by_week, current_week, max_lookahead=12):
    """Number of weeks until the next week with any historical detection.

    Returns None if no detections occur within `max_lookahead` weeks.
    """
    n = len(frequency_by_week)
    for i in range(1, max_lookahead + 1):
        if frequency_by_week[(current_week + i) % n] > 0:
            return i
    return None


def _is_in_active_window(current_week, arrival_week, departure_week, tolerance=2):
    """Return True when current_week sits within the seasonal window.

    Retained for any external callers; classify_status no longer uses it.
    Handles both normal (arrival < departure) and wrap-around (e.g. winter
    species spanning Dec -> Feb) cases.
    """
    lo = (arrival_week - tolerance) % WEEKS_PER_YEAR
    hi = (departure_week + tolerance) % WEEKS_PER_YEAR
    if lo <= hi:
        return lo <= current_week <= hi
    return current_week >= lo or current_week <= hi


def compute_predictions(week_rows, meta_rows, today=None, min_detections=3):
    """Build per-species seasonal predictions.

    Parameters:
        week_rows: list of dicts with sci_name, com_name, year, week, count.
        meta_rows: list of dicts with sci_name, total_count, first_ever,
            last_seen, first_this_year.
        today: optional date override (used in tests).
        min_detections: skip species with fewer total detections than this.

    Returns:
        dict with:
            "current_week": int,
            "current_year": int,
            "years_in_data": int (distinct calendar years with any data),
            "species": list of per-species records.
    """
    today = today or date.today()
    current_week = int(today.strftime("%W"))
    current_year = today.year

    meta_map = {m["sci_name"]: m for m in meta_rows}

    # Distinct calendar years across the entire dataset (used as denominator
    # for frequency_by_week and as a confidence indicator).
    all_years = {r["year"] for r in week_rows}
    years_in_data = max(len(all_years), 1)

    by_species = {}
    for r in week_rows:
        sn = r["sci_name"]
        spec = by_species.setdefault(sn, {
            "com_name": r["com_name"],
            "sci_name": sn,
            "year_weeks": {},  # year -> {week -> count}
        })
        spec["year_weeks"].setdefault(r["year"], {})[r["week"]] = r["count"]

    species_out = []
    for sn, spec in by_species.items():
        meta = meta_map.get(sn, {})
        total = meta.get("total_count", 0) or 0
        if total < min_detections:
            continue

        year_weeks = spec["year_weeks"]
        years_observed = len(year_weeks)

        # Per-year arrival / departure weeks
        first_weeks = [min(w.keys()) for w in year_weeks.values() if w]
        last_weeks = [max(w.keys()) for w in year_weeks.values() if w]

        arrival_week = _safe_median(first_weeks)
        departure_week = _safe_median(last_weeks)

        # Total counts per week across all years
        weekly_totals = [0] * WEEKS_PER_YEAR
        weeks_seen = set()
        for weeks in year_weeks.values():
            for w, c in weeks.items():
                if 0 <= w < WEEKS_PER_YEAR:
                    weekly_totals[w] += c
                    weeks_seen.add(w)
        peak_count = max(weekly_totals) if weekly_totals else 0
        peak_week = weekly_totals.index(peak_count) if peak_count > 0 else None

        # Frequency: fraction of years (in dataset) where this species was
        # detected in week w. Capped at 1.0.
        frequency_by_week = []
        for w in range(WEEKS_PER_YEAR):
            years_with_w = sum(1 for weeks in year_weeks.values() if w in weeks)
            frequency_by_week.append(round(min(years_with_w / years_in_data, 1.0), 3))

        last_seen = meta.get("last_seen")
        last_seen_date = _parse_date(last_seen)
        days_since = _days_between(last_seen_date, today)

        first_this_year = meta.get("first_this_year")
        detected_this_year = first_this_year is not None

        status = classify_status(
            frequency_by_week=frequency_by_week,
            current_week=current_week,
            days_since_last_seen=days_since,
            years_observed=years_observed,
            weeks_observed_count=len(weeks_seen),
            detected_this_year=detected_this_year,
        )

        weeks_until_expected = None
        if status == "coming_soon":
            weeks_until_expected = _next_active_week_offset(
                frequency_by_week, current_week, max_lookahead=12)

        species_out.append({
            "com_name": spec["com_name"],
            "sci_name": sn,
            "total_detections": total,
            "years_observed": years_observed,
            "weeks_observed_count": len(weeks_seen),
            "arrival_week": arrival_week,
            "departure_week": departure_week,
            "peak_week": peak_week,
            "peak_week_count": peak_count,
            "frequency_by_week": frequency_by_week,
            "first_ever": meta.get("first_ever"),
            "first_this_year": first_this_year,
            "last_seen": last_seen,
            "days_since_last_seen": days_since,
            "detected_this_year": detected_this_year,
            "status": status,
            "weeks_until_expected": weeks_until_expected,
        })

    # Default sort: most "actionable" first — coming_soon, expected_now, overdue,
    # then present species, then everything else, alpha within each bucket.
    status_order = {
        "expected_now": 0,
        "coming_soon": 1,
        "overdue": 2,
        "late_season": 3,
        "present": 4,
        "out_of_season": 5,
        "insufficient_data": 6,
    }
    species_out.sort(key=lambda r: (status_order.get(r["status"], 99),
                                    r["weeks_until_expected"] or 0,
                                    r["com_name"].lower()))

    return {
        "current_week": current_week,
        "current_year": current_year,
        "years_in_data": years_in_data,
        "species": species_out,
    }
