from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timezone, timedelta
from typing import Any

import swisseph as swe

from .constants import _RASHI_NAMES


_TZ_NAME = "GMT+5.5"
_TZ_OBJ = timezone(timedelta(hours=5, minutes=30))


def _mod12_1_based(n: int) -> int:
    return ((int(n) - 1) % 12) + 1


def _saturn_rashi_at_local_noon(*, d: Date) -> dict[str, Any]:
    dt_local = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=_TZ_OBJ)
    dt_utc = dt_local.astimezone(timezone.utc)
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )

    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    res, _ = swe.calc_ut(jd, swe.SATURN, int(swe.FLG_SIDEREAL))
    lon = float(res[0]) % 360.0
    rashi = int(lon / 30.0) + 1
    return {
        "date": d.isoformat(),
        "datetime_local": dt_local.isoformat(),
        "tz": _TZ_NAME,
        "saturn_lon": round(lon, 6),
        "saturn_rashi": rashi,
        "saturn_sign": _RASHI_NAMES.get(rashi, "—"),
    }


@dataclass
class _Segment:
    start: Date
    end: Date


def _saturn_rashi_series(*, start: Date, end: Date) -> list[tuple[Date, int]]:
    series: list[tuple[Date, int]] = []
    d = start
    one = timedelta(days=1)
    while d <= end:
        sat = _saturn_rashi_at_local_noon(d=d)
        series.append((d, int(sat["saturn_rashi"])))
        d = d + one
    return series


def _segments_from_series(*, series: list[tuple[Date, int]], match_rashi: int) -> list[_Segment]:
    segments: list[_Segment] = []
    cur_start: Date | None = None

    for idx, (d, rashi) in enumerate(series):
        is_match = int(rashi) == int(match_rashi)

        if is_match and cur_start is None:
            cur_start = d
        if (not is_match) and cur_start is not None:
            prev_d = series[idx - 1][0] if idx > 0 else d
            segments.append(_Segment(start=cur_start, end=prev_d))
            cur_start = None

    if cur_start is not None and series:
        segments.append(_Segment(start=cur_start, end=series[-1][0]))

    return segments


def _segment_to_dict(seg: _Segment) -> dict[str, Any]:
    days = (seg.end - seg.start).days + 1
    return {
        "start": seg.start.isoformat(),
        "end": seg.end.isoformat(),
        "days": days,
        "approx_months": round(days / 30.4375, 1),
    }


def calculate_sade_sati(*, kundli: dict[str, Any], for_date: Date | None = None) -> dict[str, Any]:
    """Compute Shani Sade Sati phase windows using Saturn sidereal sign.

    Definition used:
      - Phase 1 (Rising): Saturn in 12th from natal Moon sign
      - Phase 2 (Peak):   Saturn in natal Moon sign
      - Phase 3 (Setting):Saturn in 2nd from natal Moon sign

    Note: Saturn retrograde can cause multiple segments per phase; we return all segments.
    """

    planets = kundli.get("planets") or []
    moon = next((p for p in planets if str(p.get("name")) == "Moon"), None)
    natal_moon_rashi = int(moon.get("rashi")) if moon and moon.get("rashi") else None

    if natal_moon_rashi is None:
        return {
            "ok": False,
            "error": "Moon position missing in kundli",
        }

    target_rising = _mod12_1_based(natal_moon_rashi - 1)
    target_peak = _mod12_1_based(natal_moon_rashi)
    target_setting = _mod12_1_based(natal_moon_rashi + 1)

    # Scan a broad range around today to find the Sade Sati window.
    # 15 years each side is safe for at least one full cycle.
    base = for_date or Date.today()
    scan_start = Date(base.year - 15, 1, 1)
    scan_end = Date(base.year + 15, 12, 31)

    series = _saturn_rashi_series(start=scan_start, end=scan_end)
    rising_segments = _segments_from_series(series=series, match_rashi=target_rising)
    peak_segments = _segments_from_series(series=series, match_rashi=target_peak)
    setting_segments = _segments_from_series(series=series, match_rashi=target_setting)

    # Find an overall window around `base`.
    def _contains(segs: list[_Segment], d: Date) -> _Segment | None:
        for s in segs:
            if s.start <= d <= s.end:
                return s
        return None

    # Determine current phase.
    current_phase = None
    current_severity = None
    if _contains(peak_segments, base):
        current_phase = "peak"
        current_severity = "high"
    elif _contains(rising_segments, base):
        current_phase = "rising"
        current_severity = "medium"
    elif _contains(setting_segments, base):
        current_phase = "setting"
        current_severity = "medium"

    is_active = current_phase is not None

    sat_today = _saturn_rashi_at_local_noon(d=base)

    # Determine the nearest (current or next) cycle window by looking at phase boundaries.
    all_segments = (
        [("rising", "medium", rising_segments, target_rising)]
        + [("peak", "high", peak_segments, target_peak)]
        + [("setting", "medium", setting_segments, target_setting)]
    )

    # Pick the cycle whose rising start is closest <= base, else the next rising.
    rising_starts = [s.start for s in rising_segments]
    rising_starts.sort()
    cycle_start = None
    for rs in reversed(rising_starts):
        if rs <= base:
            cycle_start = rs
            break
    if cycle_start is None and rising_starts:
        cycle_start = rising_starts[0]

    # Find the first rising segment that begins at cycle_start.
    cycle_rising = next((s for s in rising_segments if s.start == cycle_start), None)

    # The cycle end is the last setting segment that starts after cycle_start and within ~10 years.
    cycle_end = None
    if cycle_start is not None:
        cutoff = Date(cycle_start.year + 10, 12, 31)
        cand = [s for s in setting_segments if s.start >= cycle_start and s.start <= cutoff]
        if cand:
            cand.sort(key=lambda x: x.end)
            cycle_end = cand[-1].end

    # Build phase rows (all segments), but keep display-friendly structure.
    phases: list[dict[str, Any]] = []
    for phase, severity, segs, target in all_segments:
        rows = []
        for seg in segs:
            # Only include segments that overlap the selected cycle window when we have one.
            if cycle_start and cycle_end:
                if seg.end < cycle_start or seg.start > cycle_end:
                    continue
            rows.append(_segment_to_dict(seg))

        phases.append(
            {
                "phase": phase,
                "label": {"rising": "Rising (12th from Moon)", "peak": "Peak (on Moon)", "setting": "Setting (2nd from Moon)"}[phase],
                "severity": severity,
                "saturn_target_rashi": target,
                "saturn_target_sign": _RASHI_NAMES.get(target, "—"),
                "segments": rows,
            }
        )

    problems: list[dict[str, Any]] = []
    if is_active:
        problems.append(
            {
                "key": "sade_sati",
                "title": "Sade Sati active",
                "detail": f"Current phase: {current_phase} (severity: {current_severity}).",
            }
        )

    remedies: list[dict[str, Any]] = []

    # Always provide a gentle Shani remedy set, and add stronger advice during peak.
    remedies.append(
        {
            "title": "Saturday discipline remedy (general)",
            "type": "behavior",
            "when": "Saturday",
            "why": "Helps cultivate Saturn qualities: discipline, patience, responsibility.",
            "steps": [
                "Wake up on time; keep a simple routine.",
                "Avoid lying and shortcuts; keep promises small and realistic.",
                "Help an elderly person or someone in need (optional).",
            ],
        }
    )

    remedies.append(
        {
            "title": "Shani mantra (general)",
            "type": "chant",
            "when": "Saturday evening",
            "why": "Commonly suggested for Shani-related challenges.",
            "steps": [
                "Chant 'Om Sham Shanicharaya Namah' 108 times.",
                "Light a sesame oil diya (optional) in a safe place.",
                "Keep thoughts calm; avoid resentment.",
            ],
        }
    )

    if current_phase == "peak":
        remedies.append(
            {
                "title": "Peak-phase support",
                "type": "donation",
                "when": "Saturday (optional)",
                "why": "Peak phase can feel heavier; grounding actions can help.",
                "steps": [
                    "Donate black sesame, warm clothing, or food to the needy (optional).",
                    "Avoid major risky decisions; focus on steady work.",
                    "Prioritize sleep and consistent habits.",
                ],
            }
        )

    return {
        "ok": True,
        "for_date": base.isoformat(),
        "timezone": _TZ_NAME,
        "natal": {
            "moon_rashi": natal_moon_rashi,
            "moon_sign": _RASHI_NAMES.get(natal_moon_rashi, "—"),
        },
        "today": {
            "saturn_rashi": sat_today["saturn_rashi"],
            "saturn_sign": sat_today["saturn_sign"],
        },
        "targets": {
            "rising": target_rising,
            "peak": target_peak,
            "setting": target_setting,
        },
        "status": {
            "is_active": is_active,
            "current_phase": current_phase,
            "current_severity": current_severity,
            "cycle_start": cycle_start.isoformat() if cycle_start else None,
            "cycle_end": cycle_end.isoformat() if cycle_end else None,
        },
        "phases": phases,
        "problems": problems,
        "remedies": remedies,
        "disclaimer": "Sade Sati calculation is approximate (daily sampling) and for guidance only.",
    }


def build_sade_sati_timeline(*, kundli: dict[str, Any], start: Date, end: Date) -> dict[str, Any]:
    """Build a full Sade Sati timeline between [start, end].

    Returns a flat, tabular list of segments with:
      - start, end (ISO)
      - sign_name
      - phase (rising|peak|setting)
      - type (Rising|Peak|Setting)

    This is intended for persistence so the frontend doesn't need to recompute.
    """

    planets = kundli.get("planets") or []
    moon = next((p for p in planets if str(p.get("name")) == "Moon"), None)
    natal_moon_rashi = int(moon.get("rashi")) if moon and moon.get("rashi") else None

    if natal_moon_rashi is None:
        return {
            "ok": False,
            "error": "Moon position missing in kundli",
        }

    start_d = start
    end_d = end
    if end_d < start_d:
        start_d, end_d = end_d, start_d

    target_rising = _mod12_1_based(natal_moon_rashi - 1)
    target_peak = _mod12_1_based(natal_moon_rashi)
    target_setting = _mod12_1_based(natal_moon_rashi + 1)

    series = _saturn_rashi_series(start=start_d, end=end_d)
    rising_segments = _segments_from_series(series=series, match_rashi=target_rising)
    peak_segments = _segments_from_series(series=series, match_rashi=target_peak)
    setting_segments = _segments_from_series(series=series, match_rashi=target_setting)

    rows: list[dict[str, Any]] = []

    def _add_rows(phase: str, label: str, segs: list[_Segment], target_rashi: int) -> None:
        sign_name = _RASHI_NAMES.get(target_rashi, "—")
        for seg in segs:
            rows.append(
                {
                    "start": seg.start.isoformat(),
                    "end": seg.end.isoformat(),
                    "sign_name": sign_name,
                    "phase": phase,
                    "type": label,
                }
            )

    _add_rows("rising", "Rising", rising_segments, target_rising)
    _add_rows("peak", "Peak", peak_segments, target_peak)
    _add_rows("setting", "Setting", setting_segments, target_setting)

    rows.sort(key=lambda r: (r.get("start") or "", r.get("phase") or ""))

    return {
        "ok": True,
        "range": {"start": start_d.isoformat(), "end": end_d.isoformat()},
        "natal": {
            "moon_rashi": natal_moon_rashi,
            "moon_sign": _RASHI_NAMES.get(natal_moon_rashi, "—"),
        },
        "rows": rows,
        "disclaimer": "Sade Sati calculation is approximate (daily sampling) and for guidance only.",
    }
