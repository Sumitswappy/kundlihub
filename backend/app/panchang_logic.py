"""Panchang, Nakshatra, and Avakhada-related calculations."""

from __future__ import annotations

from datetime import datetime, timezone

import swisseph as swe

from .constants import (
    _NAKSHATRA_NAMES,
    _NAKSHATRA_PADA_SYLLABLES,
    _VIMSHOTTARI_ORDER,
    _YOGA_NAMES,
)
from .utils import _format_hms, _jd_to_local_time


def _nakshatra_lord_from_lon(lon: float) -> str:
    # Lords repeat every 9 nakshatras.
    segment = 360.0 / 27.0
    idx0 = int((float(lon) % 360.0) / segment)
    return _VIMSHOTTARI_ORDER[idx0 % 9]


def _calc_sunrise_sunset(dob: str, tz, lat: float, lon: float) -> tuple[str | None, str | None]:
    # Use local midnight as the start time so we get sunrise/sunset for the local civil date.
    local_date = datetime.strptime(dob, "%Y-%m-%d").date()
    dt0_local = datetime(local_date.year, local_date.month, local_date.day, 0, 0, 0, tzinfo=tz)
    dt0_utc = dt0_local.astimezone(timezone.utc)
    jd0 = swe.julday(dt0_utc.year, dt0_utc.month, dt0_utc.day, dt0_utc.hour + dt0_utc.minute / 60.0)

    def _call_rise_trans(jd_start: float, rsmi: int):
        # pyswisseph has had a few signature variants across versions.
        # Current (documented) signature:
        #   rise_trans(tjdut, body, rsmi, geopos, atpress=0.0, attemp=0.0, flags=FLG_SWIEPH)
        geopos = (float(lon), float(lat), 0.0)

        try:
            return swe.rise_trans(jd_start, swe.SUN, rsmi, geopos, 0.0, 0.0, swe.FLG_SWIEPH)
        except TypeError:
            pass

        try:
            return swe.rise_trans(jd_start, swe.SUN, rsmi, geopos)
        except TypeError:
            pass

        # Older variants / keyword variants.
        try:
            return swe.rise_trans(jd_start, swe.SUN, geopos, rsmi=rsmi)
        except TypeError:
            pass

        return swe.rise_trans(jd_start, swe.SUN, lon, lat, rsmi=rsmi)

    sunrise = None
    sunset = None
    try:
        _, tret_rise = _call_rise_trans(jd0, int(swe.CALC_RISE) | int(swe.BIT_DISC_CENTER))
        sunrise = _format_hms(_jd_to_local_time(float(tret_rise[0]), tz))
    except Exception:
        sunrise = None
    try:
        _, tret_set = _call_rise_trans(jd0, int(swe.CALC_SET) | int(swe.BIT_DISC_CENTER))
        sunset = _format_hms(_jd_to_local_time(float(tret_set[0]), tz))
    except Exception:
        sunset = None

    return sunrise, sunset


def _nakshatra_from_lon(moon_lon: float) -> tuple[str, int, str]:
    # 27 nakshatras, each 13°20' = 13.333333... degrees
    segment = 360.0 / 27.0
    pada_size = segment / 4.0
    idx0 = int((moon_lon % 360.0) / segment)
    name = _NAKSHATRA_NAMES[idx0]
    pada = int(((moon_lon % segment) / pada_size)) + 1
    syllables = _NAKSHATRA_PADA_SYLLABLES.get(name, ["—", "—", "—", "—"])
    syllable = syllables[pada - 1] if 1 <= pada <= 4 else "—"
    return name, pada, syllable


def _yoga_from_sun_moon(sun_lon: float, moon_lon: float) -> str:
    segment = 360.0 / 27.0
    idx0 = int(((sun_lon + moon_lon) % 360.0) / segment)
    return _YOGA_NAMES[idx0]


def _karana_from_elongation(elongation: float) -> str:
    # Each tithi is 12°; each karana is 6° => 60 half-tithis.
    half_tithi = int((elongation % 360.0) / 6.0) + 1  # 1..60

    if half_tithi == 1:
        return "Kimstughna"
    if half_tithi == 58:
        return "Shakuni"
    if half_tithi == 59:
        return "Chatushpada"
    if half_tithi == 60:
        return "Nagava"

    movable = ["Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti"]
    return movable[(half_tithi - 2) % 7]


def _varna_from_rashi(rashi_num: int) -> str:
    # Common varna mapping by rashi element.
    if rashi_num in (4, 8, 12):
        return "Brahmin"  # water
    if rashi_num in (1, 5, 9):
        return "Kshatriya"  # fire
    if rashi_num in (2, 6, 10):
        return "Vaishya"  # earth
    if rashi_num in (3, 7, 11):
        return "Shudra"  # air
    return "—"


def _vashya_from_rashi(rashi_num: int) -> str:
    # Common vashya mapping used in many Panchang/Kundli calculators.
    return {
        1: "Chatushpada",
        2: "Chatushpada",
        3: "Nara",
        4: "Jalchar",
        5: "Vanachara",
        6: "Nara",
        7: "Nara",
        8: "Keeta",
        9: "Vanachara",
        10: "Chatushpada",
        11: "Nara",
        12: "Jalchar",
    }.get(rashi_num, "—")


def _nadi_from_nakshatra_index(nak_index_1_based: int) -> str:
    # Standard repeating nadi pattern: Aadi, Madhya, Antya
    mod = (nak_index_1_based - 1) % 3
    return ["Aadi", "Madhya", "Antya"][mod]


def _paya_from_moon_house(lagna_rashi: int, moon_rashi: int) -> tuple[str, int]:
    """Return (label, moon_house).

    Uses whole-sign house counting from Lagna to Moon rashi:
      1/3/6  -> Swarna (Gold)
      2/5/9  -> Rajat (Silver)
      3/7/10 -> Tamra (Copper)
      4/8/12 -> Loha (Iron)
    """

    moon_house = ((int(moon_rashi) - int(lagna_rashi)) % 12) + 1
    # Note: 3rd house is listed in both Gold and Copper rules in the provided spec.
    # We treat rule order as precedence (Gold checked first).
    if moon_house in (1, 3, 6):
        return "Swarna (Gold)", moon_house
    if moon_house in (2, 5, 9):
        return "Rajat (Silver)", moon_house
    if moon_house in (3, 7, 10):
        return "Tamra (Copper)", moon_house
    return "Loha (Iron)", moon_house


def _paya_from_nakshatra(nakshatra_name: str) -> str:
    def _key(s: str) -> str:
        return "".join(ch for ch in str(s).lower() if ch.isalnum())

    key = _key(nakshatra_name)

    canonical_by_key = {_key(n): n for n in _NAKSHATRA_NAMES}
    aliases = {
        # Common spelling/spacing variants
        "adra": "Ardra",
        "purnavasu": "Punarvasu",
        "ashlesha": "Ashlesha",
        "purvaphalguni": "Purva Phalguni",
        "uttaraphalguni": "Uttara Phalguni",
        "vishakha": "Vishakha",
        "jyeshta": "Jyeshtha",
        "moola": "Mula",
        "purvaashadha": "Purva Ashadha",
        "uttaraashadha": "Uttara Ashadha",
        "shravana": "Shravana",
        "dhanishta": "Dhanishta",
        "satabisha": "Shatabhisha",
        "satabhisha": "Shatabhisha",
        "purvaphadra": "Purva Bhadrapada",
        "purvabhadra": "Purva Bhadrapada",
        "uttarabhaadra": "Uttara Bhadrapada",
        "uttarabhadra": "Uttara Bhadrapada",
    }

    canonical = canonical_by_key.get(key) or aliases.get(key) or nakshatra_name

    silver = {
        "Ardra",
        "Punarvasu",
        "Pushya",
        "Ashlesha",
        "Magha",
        "Purva Phalguni",
        "Uttara Phalguni",
        "Hasta",
        "Chitra",
        "Swati",
        "Vishakha",
        "Anuradha",
    }
    copper = {
        "Jyeshtha",
        "Mula",
        "Purva Ashadha",
        "Uttara Ashadha",
        "Shravana",
        "Dhanishta",
        "Shatabhisha",
        "Purva Bhadrapada",
        "Uttara Bhadrapada",
    }
    gold = {"Revati", "Ashwini", "Bharani"}

    if canonical in gold:
        return "Swarna (Gold)"
    if canonical in silver:
        return "Rajat (Silver)"
    if canonical in copper:
        return "Tamra (Copper)"
    return "Loha (Iron)"
