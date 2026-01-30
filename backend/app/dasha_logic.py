"""Vimshottari dasha calculations."""

from __future__ import annotations

from datetime import datetime

from .constants import _VIMSHOTTARI_ORDER, _VIMSHOTTARI_YEARS
from .utils import _add_years_approx, _add_years_calendar


def calc_vimshottari_subperiods(
    parent_planet: str,
    start_date: str,
    end_date: str,
    parent_total_years: float,
    offset_years: float = 0.0,
) -> list[dict]:
    """Compute Vimshottari sub-periods clipped to a window.

    We treat the sub-period schedule as defined over the *canonical* full parent dasha
    duration (parent_total_years). The provided start_date/end_date represent a window
    that begins offset_years into the canonical parent timeline.

    This is critical for "partial" periods (e.g., running Mahadasha remainder at birth),
    where we should start from the currently-running Antardasha (not always from the first).

    Returns rows containing:
      planet, start_date, end_date, years, total_years, offset_years
    where total_years/offset_years are relative to the *returned row's* canonical duration,
    enabling correct deeper drill-down.
    """
    parent = str(parent_planet or "").strip()
    if parent not in _VIMSHOTTARI_ORDER:
        raise ValueError(f"Invalid parent planet: {parent}")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    if end_dt <= start_dt:
        raise ValueError("end_date must be after start_date")

    total_years = float(parent_total_years)
    if not (total_years > 0):
        raise ValueError("parent_total_years must be > 0")

    win_start = float(offset_years or 0.0)
    if win_start < 0:
        raise ValueError("offset_years must be >= 0")

    win_years = (end_dt - start_dt).total_seconds() / 86400.0 / 365.2425
    win_end = win_start + win_years

    start_i = _VIMSHOTTARI_ORDER.index(parent)
    periods: list[dict] = []

    def _fmt(d: datetime) -> str:
        return d.strftime("%Y-%m-%d")

    # Build canonical subperiod boundaries in years from parent start.
    cursor_y = 0.0
    for k in range(9):
        lord = _VIMSHOTTARI_ORDER[(start_i + k) % 9]
        seg_total = total_years * (float(_VIMSHOTTARI_YEARS[lord]) / 120.0)
        seg_start = cursor_y
        seg_end = seg_start + seg_total
        cursor_y = seg_end

        # Intersection with window [win_start, win_end]
        clip_start = max(seg_start, win_start)
        clip_end = min(seg_end, win_end)
        if clip_end <= clip_start:
            continue

        # Map clipped years back to dates relative to start_date (which corresponds to win_start)
        start_out = _add_years_approx(start_dt, clip_start - win_start)
        end_out = _add_years_approx(start_dt, clip_end - win_start)

        # Offset within this returned row (for next drill-down)
        row_offset = clip_start - seg_start
        row_years = clip_end - clip_start

        periods.append(
            {
                "planet": lord,
                "start_date": _fmt(start_out),
                "end_date": _fmt(end_out),
                "years": round(row_years, 6),
                "total_years": round(seg_total, 6),
                "offset_years": round(row_offset, 6),
            }
        )

    # Drift guard: ensure exact final end_date matches window end when present.
    if periods:
        periods[-1]["end_date"] = end_date

    return periods


def _calc_vimshottari_mahadasha(dob: str, tob: str, moon_lon: float) -> list[dict]:
    """Compute Vimshottari Mahadasha list starting from birth.

    Returns a list of dicts like:
      { planet, start_date, end_date, start_label? }

    The first period is the remaining portion of the running Mahadasha at birth.
    """
    # For UI-style Vimshottari tables, use civil date boundaries (ignore time-of-day)
    # to match common reference outputs.
    birth_dt = datetime.strptime(dob, "%Y-%m-%d")

    segment = 360.0 / 27.0
    moon_pos_in_nak = float(moon_lon) % segment
    elapsed_frac = moon_pos_in_nak / segment

    nak_idx0 = int((float(moon_lon) % 360.0) / segment)
    current_lord = _VIMSHOTTARI_ORDER[nak_idx0 % 9]
    current_years = float(_VIMSHOTTARI_YEARS[current_lord])

    remaining_years = current_years * (1.0 - elapsed_frac)
    offset_years = current_years * elapsed_frac

    # Build 9 periods from birth onward (current remainder + next 8 full mahadashas)
    order = _VIMSHOTTARI_ORDER
    start_i = order.index(current_lord)

    periods: list[dict] = []
    start_dt = birth_dt

    def _fmt(d: datetime) -> str:
        return d.strftime("%Y-%m-%d")

    # First (partial) period
    end_dt = _add_years_approx(start_dt, remaining_years)
    end_dt = datetime(end_dt.year, end_dt.month, end_dt.day)
    periods.append(
        {
            "planet": current_lord,
            "start_date": _fmt(start_dt),
            "end_date": _fmt(end_dt),
            "start_label": "Birth",
            "years": round(remaining_years, 6),
            "total_years": round(current_years, 6),
            "offset_years": round(offset_years, 6),
        }
    )

    # Subsequent full periods
    cursor = end_dt
    for k in range(1, 9):
        lord = order[(start_i + k) % 9]
        yrs = float(_VIMSHOTTARI_YEARS[lord])
        # Full mahadashas should align to calendar boundaries.
        nxt = _add_years_calendar(cursor, int(yrs))
        periods.append(
            {
                "planet": lord,
                "start_date": _fmt(cursor),
                "end_date": _fmt(nxt),
                "years": round(yrs, 6),
                "total_years": round(yrs, 6),
                "offset_years": 0.0,
            }
        )
        cursor = nxt

    return periods
