from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

import swisseph as swe

from .constants import _RASHI_NAMES
from .panchang_logic import _nakshatra_from_lon


_TZ_NAME = "GMT+5.5"
_TZ_OBJ = timezone(timedelta(hours=5, minutes=30))


def _moon_transit_at_local_noon(*, for_date: date, lat: float, lon: float) -> dict[str, Any]:
    """Return sidereal Moon transit snapshot for a given local civil date.

    We use local noon to avoid edge cases near midnight.
    """

    dt_local = datetime(for_date.year, for_date.month, for_date.day, 12, 0, 0, tzinfo=_TZ_OBJ)
    dt_utc = dt_local.astimezone(timezone.utc)

    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )

    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    res, _ = swe.calc_ut(jd, swe.MOON, int(swe.FLG_SIDEREAL))
    moon_lon = float(res[0]) % 360.0

    rashi = int(moon_lon / 30.0) + 1
    nak_name, nak_pada, _ = _nakshatra_from_lon(moon_lon)

    return {
        "datetime_local": dt_local.isoformat(),
        "tz": _TZ_NAME,
        "moon_lon": round(moon_lon, 6),
        "moon_rashi": rashi,
        "moon_sign": _RASHI_NAMES.get(rashi, "—"),
        "moon_nakshatra": nak_name,
        "moon_nakshatra_pada": nak_pada,
        # keep lat/lon as context
        "lat": float(lat),
        "lon": float(lon),
    }


def _house_from_sign(*, base_rashi: int, target_rashi: int) -> int:
    return ((int(target_rashi) - int(base_rashi)) % 12) + 1


def _sentiment_from_house(house_from_moon: int) -> tuple[str, int]:
    """Return (sentiment, score 0-100)"""

    if house_from_moon in (6, 8, 12):
        return "challenging", 35
    if house_from_moon in (3, 10, 11):
        return "good", 75
    if house_from_moon in (1, 2, 4, 5, 7, 9):
        return "mixed", 55
    # fallback
    return "mixed", 50


def _weekday(dt_local_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_local_iso)
        return dt.strftime("%A")
    except Exception:
        return "—"


def _remedy_for_weekday(day: str) -> dict[str, Any] | None:
    # Light, non-controversial, culturally common suggestions.
    remedies = {
        "Monday": {
            "title": "Monday calmness remedy",
            "type": "chant",
            "when": "Morning",
            "steps": [
                "Offer water to the Sun (optional) and sit quietly for 5 minutes.",
                "Chant 'Om Som Somaya Namah' 108 times.",
                "Avoid overthinking; keep your schedule light.",
            ],
        },
        "Tuesday": {
            "title": "Tuesday energy-balancing remedy",
            "type": "behavior",
            "when": "Evening",
            "steps": [
                "Read or listen to Hanuman Chalisa once.",
                "Avoid arguments and impulsive decisions.",
                "If donating, consider red lentils or jaggery (optional).",
            ],
        },
        "Wednesday": {
            "title": "Wednesday clarity remedy",
            "type": "behavior",
            "when": "Anytime",
            "steps": [
                "Write down 3 priorities for the day.",
                "Speak less, listen more in important conversations.",
                "Donate stationery or help a student (optional).",
            ],
        },
        "Thursday": {
            "title": "Thursday guidance remedy",
            "type": "donation",
            "when": "Morning",
            "steps": [
                "Offer respect to teachers/elders.",
                "If donating, consider turmeric, yellow sweets, or bananas (optional).",
                "Chant 'Om Gurave Namah' 108 times.",
            ],
        },
        "Friday": {
            "title": "Friday harmony remedy",
            "type": "behavior",
            "when": "Anytime",
            "steps": [
                "Keep your space clean and pleasant.",
                "Do one act of kindness for family/partner.",
                "Chant 'Om Shukraya Namah' 108 times (optional).",
            ],
        },
        "Saturday": {
            "title": "Saturday patience remedy",
            "type": "donation",
            "when": "Evening",
            "steps": [
                "Avoid shortcuts; do tasks slowly and correctly.",
                "If donating, consider black sesame or helping the needy (optional).",
                "Chant 'Om Sham Shanicharaya Namah' 108 times.",
            ],
        },
        "Sunday": {
            "title": "Sunday confidence remedy",
            "type": "behavior",
            "when": "Morning",
            "steps": [
                "Get sunlight for a few minutes (as comfortable).",
                "Set one bold but realistic goal for the week.",
                "Chant 'Om Suryaya Namah' 108 times (optional).",
            ],
        },
    }
    return remedies.get(day)


def _clip_score(n: int) -> int:
    return max(0, min(int(n), 100))


def _sentiment_from_score(score: int) -> str:
    if score >= 70:
        return "good"
    if score <= 40:
        return "challenging"
    return "mixed"


def _area_breakdown(
    *,
    house_from_moon: int | None,
    manglik_present: bool,
    kalsarpa_present: bool,
) -> dict[str, Any]:
    """Return per-area (career/finance/love) guidance.

    This is intentionally lightweight and explainable: it uses Moon transit from natal Moon
    and applies small score adjustments for natal doshas.
    """

    h = int(house_from_moon or 0)

    # Base scores around "mixed".
    career_score = 55
    finance_score = 55
    love_score = 55
    health_score = 55

    # Moon-from-Moon heuristics
    if h in (10, 11, 3):
        career_score += 18
    elif h in (6,):
        career_score += 6  # work pressure but productive
    elif h in (8, 12):
        career_score -= 15

    if h in (2, 11, 9, 10):
        finance_score += 15
    elif h in (6, 12, 8):
        finance_score -= 18
    elif h in (5,):
        finance_score += 5

    if h in (5, 7, 9, 11):
        love_score += 15
    elif h in (6, 8, 12):
        love_score -= 18
    elif h in (2, 4):
        love_score += 5

    # Health: Moon heavy houses can affect rest/mood; 6th can be regimen-heavy.
    if h in (6,):
        health_score -= 8
    elif h in (8, 12):
        health_score -= 18
    elif h in (1, 3, 11):
        health_score += 10
    elif h in (4, 5, 9):
        health_score += 5

    # Natal dosha adjustments
    if manglik_present:
        love_score -= 15
        career_score -= 3
        health_score -= 5
    if kalsarpa_present:
        career_score -= 10
        finance_score -= 10
        love_score -= 5
        health_score -= 8

    career_score = _clip_score(career_score)
    finance_score = _clip_score(finance_score)
    love_score = _clip_score(love_score)
    health_score = _clip_score(health_score)

    def _pack(area: str, score: int) -> dict[str, Any]:
        sentiment = _sentiment_from_score(score)
        if area == "career":
            do = ["Prioritize one high-impact task", "Follow up and communicate clearly"]
            dont = ["Avoid impulsive job decisions", "Avoid multitasking overload"]
            summary = "Steady progress with focused effort."
            if h in (10, 11, 3):
                summary = "Strong day for productivity, meetings, and momentum."
            elif h in (6,):
                summary = "Work may feel heavy, but effort pays off."
            elif h in (8, 12):
                summary = "Keep things low-risk; avoid major switches today."
        elif area == "finance":
            do = ["Track expenses", "Stick to a budget or savings plan"]
            dont = ["Avoid speculative trades", "Avoid lending money impulsively"]
            summary = "Keep spending practical and review numbers calmly."
            if h in (2, 11, 9, 10):
                summary = "Good for gains, planning, and financial follow-ups."
            elif h in (6, 12, 8):
                summary = "Watch expenses; delay risky purchases and investments."
        else:
            if area == "health":
                do = ["Hydrate and eat light", "Take a short walk or stretching"]
                dont = ["Avoid late-night screen time", "Avoid overexertion"]
                summary = "Keep routine steady; small habits help most today."
                if h in (1, 3, 11):
                    summary = "Good vitality—use it for consistent healthy routines."
                elif h in (6,):
                    summary = "Mind your schedule and digestion; prioritize rest."
                elif h in (8, 12):
                    summary = "Low-energy day—avoid strain and get adequate sleep."

                if manglik_present:
                    do = ["Channel energy into exercise safely", "Practice cooling breathwork"] + do
                    dont = ["Avoid spicy food if it triggers", "Avoid rushing or impulsive activity"] + dont
                if kalsarpa_present:
                    do = ["Keep timings fixed (sleep/food)", "Reduce caffeine late in day"] + do
                    dont = ["Avoid skipping meals", "Avoid stressful overcommitment"] + dont

                return {
                    "sentiment": sentiment,
                    "score": score,
                    "summary": summary,
                    "do": do[:4],
                    "dont": dont[:4],
                }

            do = ["Practice patience in conversations", "Be direct but gentle"]
            dont = ["Avoid ego clashes", "Avoid bringing up old conflicts"]
            summary = "Small gestures improve harmony."
            if h in (5, 7, 9, 11):
                summary = "Good for bonding, dates, and meaningful talks."
            elif h in (6, 8, 12):
                summary = "Emotions can spike; keep expectations low and communicate softly."

        if manglik_present and area == "love":
            do = ["Channel energy into exercise", "Pause before reacting"] + do
            dont = ["Avoid heated arguments", "Avoid dominance or impatience"] + dont
        if kalsarpa_present and area in ("career", "finance"):
            do = ["Double-check commitments", "Keep paperwork and timelines tidy"] + do
            dont = ["Avoid shortcuts", "Avoid taking on uncertain obligations"] + dont

        return {
            "sentiment": sentiment,
            "score": score,
            "summary": summary,
            "do": do[:4],
            "dont": dont[:4],
        }

    return {
        "basis": {
            "moon_house_from_natal_moon": house_from_moon,
            "notes": "Career/Finance/Love are derived from Moon transit (from natal Moon) with small natal dosha adjustments.",
        },
        "career": _pack("career", career_score),
        "finance": _pack("finance", finance_score),
        "love": _pack("love", love_score),
        "health": _pack("health", health_score),
    }


def calculate_daily_horoscope(*, kundli: dict[str, Any], lat: float, lon: float, for_date: date) -> dict[str, Any]:
    planets = kundli.get("planets") or []
    doshas = kundli.get("doshas") or {}

    moon = next((p for p in planets if str(p.get("name")) == "Moon"), None)
    natal_moon_rashi = int(moon.get("rashi")) if moon and moon.get("rashi") else None
    natal_moon_nak = moon.get("nakshatra") if moon else None

    transit = _moon_transit_at_local_noon(for_date=for_date, lat=float(lat), lon=float(lon))

    house_from_moon = None
    if natal_moon_rashi is not None:
        house_from_moon = _house_from_sign(base_rashi=natal_moon_rashi, target_rashi=int(transit["moon_rashi"]))

    sentiment, score = _sentiment_from_house(int(house_from_moon or 0))

    problems: list[dict[str, Any]] = []
    if house_from_moon in (6, 8, 12):
        problems.append(
            {
                "key": "moon_transit",
                "title": "Challenging Moon transit",
                "detail": f"Today the Moon is in your {house_from_moon}th house from natal Moon.",
            }
        )

    manglik_present = bool(doshas.get("manglik", {}).get("present") is True)
    kalsarpa_present = bool(doshas.get("kalsarpa", {}).get("present") is True)

    if manglik_present:
        problems.append(
            {
                "key": "manglik",
                "title": "Manglik influence (natal)",
                "detail": "Your chart indicates Manglik influence; keep anger and impulsiveness in check.",
            }
        )

    if kalsarpa_present:
        problems.append(
            {
                "key": "kalsarpa",
                "title": "Kalsarpa influence (natal)",
                "detail": "Your chart indicates Kalsarpa influence; keep routines steady and avoid risky decisions.",
            }
        )

    remedies: list[dict[str, Any]] = []

    day = _weekday(transit["datetime_local"])
    weekday_remedy = _remedy_for_weekday(day)
    if weekday_remedy:
        weekday_remedy = {**weekday_remedy, "why": f"Recommended for {day}."}
        remedies.append(weekday_remedy)

    if house_from_moon in (6, 8, 12):
        remedies.append(
            {
                "title": "Mind & mood balancing",
                "type": "chant",
                "when": "Anytime",
                "why": "Helps on days with challenging Moon transit.",
                "steps": [
                    "Drink water mindfully and take 10 slow breaths.",
                    "Chant 'Om Chandraya Namah' 108 times (or 27 if short on time).",
                    "Avoid late-night overwork and heated discussions.",
                ],
            }
        )

    if any(p["key"] == "manglik" for p in problems):
        remedies.append(
            {
                "title": "Mars/anger pacification",
                "type": "behavior",
                "when": "Tuesday or anytime",
                "why": "Useful when Manglik influence is present.",
                "steps": [
                    "Read Hanuman Chalisa once (optional but common).",
                    "Do a small physical workout to channel Mars energy.",
                    "Donate red lentils or feed animals (optional).",
                ],
            }
        )

    if any(p["key"] == "kalsarpa" for p in problems):
        remedies.append(
            {
                "title": "Rahu–Ketu balancing",
                "type": "puja",
                "when": "Saturday / Monday (optional)",
                "why": "Commonly suggested when Kalsarpa influence is present.",
                "steps": [
                    "Chant 'Om Rahave Namah' 108 times and 'Om Ketave Namah' 108 times.",
                    "Offer water to Shiva (or do a simple Shiva prayer).",
                    "Avoid gambling/speculation and keep commitments small today.",
                ],
            }
        )

    highlights: list[str] = []
    if house_from_moon in (3, 10, 11):
        highlights = [
            "Good day for communication and planning.",
            "Effort gives visible results; keep focus.",
            "Network and follow-ups can work in your favor.",
        ]
    elif house_from_moon in (6, 8, 12):
        highlights = [
            "Keep emotions steady; avoid overreacting.",
            "Do essential tasks, postpone risky decisions.",
            "Rest and routines help more than hustle today.",
        ]
    else:
        highlights = [
            "Balanced day—progress is steady with consistency.",
            "Focus on basics: work, food, sleep, and communication.",
            "Avoid extremes; keep decisions practical.",
        ]

    return {
        "for_date": for_date.isoformat(),
        "timezone": _TZ_NAME,
        "natal": {
            "moon_rashi": natal_moon_rashi,
            "moon_sign": _RASHI_NAMES.get(natal_moon_rashi, "—") if natal_moon_rashi else "—",
            "moon_nakshatra": natal_moon_nak or "—",
        },
        "transit": {**transit, "moon_house_from_natal_moon": house_from_moon},
        "overall": {
            "sentiment": sentiment,
            "score": score,
            "summary": " ".join(highlights[:2]),
            "highlights": highlights,
        },
        "breakdown": _area_breakdown(
            house_from_moon=house_from_moon,
            manglik_present=manglik_present,
            kalsarpa_present=kalsarpa_present,
        ),
        "problems": problems,
        "remedies": remedies,
        "disclaimer": "Horoscope is guidance-only and not a substitute for professional advice.",
    }
