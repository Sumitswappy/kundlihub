"""General-purpose helpers used across astrology modules."""

from __future__ import annotations

from datetime import datetime, timezone

import swisseph as swe


def _angle_sep_deg(a: float, b: float) -> float:
    """Return the minimum absolute angular separation between two longitudes (degrees)."""
    d = abs((float(a) - float(b)) % 360.0)
    return d if d <= 180.0 else 360.0 - d


def _add_years_approx(dt: datetime, years: float) -> datetime:
    # Good-enough civil approximation for UI timelines.
    # (Avoids tricky calendar/relativedelta dependencies.)
    from datetime import timedelta

    return dt + timedelta(days=float(years) * 365.2425)


def _add_years_calendar(dt: datetime, years: int) -> datetime:
    """Add whole calendar years preserving month/day.

    This matches common Vimshottari table outputs that use civil calendar year boundaries
    (e.g., 2006-06-25 + 17y = 2023-06-25), avoiding fractional-day drift.
    """
    try:
        return dt.replace(year=dt.year + int(years))
    except ValueError:
        # Handle Feb 29 -> Feb 28 on non-leap years.
        if dt.month == 2 and dt.day == 29:
            return dt.replace(year=dt.year + int(years), day=28)
        raise


def _format_hms(dt_local: datetime) -> str:
    return dt_local.strftime("%H:%M:%S")


def _jd_to_local_time(jd_ut: float, tz) -> datetime:
    y, m, d, ut = swe.revjul(jd_ut, swe.GREG_CAL)
    hours = int(ut)
    minutes = int((ut - hours) * 60)
    seconds = int(round((((ut - hours) * 60) - minutes) * 60))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        hours += 1
    dt_utc = datetime(int(y), int(m), int(d), int(hours) % 24, int(minutes), int(seconds), tzinfo=timezone.utc)
    return dt_utc.astimezone(tz)
