import swisseph as swe
from datetime import datetime, timezone, timedelta

from zoneinfo import ZoneInfo


_NAKSHATRA_NAMES = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashirsha",
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
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

_YOGA_NAMES = [
    "Vishkumbha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shoola",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

_RASHI_NAMES = {
    1: "Aries",
    2: "Taurus",
    3: "Gemini",
    4: "Cancer",
    5: "Leo",
    6: "Virgo",
    7: "Libra",
    8: "Scorpio",
    9: "Sagittarius",
    10: "Capricorn",
    11: "Aquarius",
    12: "Pisces",
}

_RASHI_LORD = {
    1: "Mars",
    2: "Venus",
    3: "Mercury",
    4: "Moon",
    5: "Sun",
    6: "Mercury",
    7: "Venus",
    8: "Mars",
    9: "Jupiter",
    10: "Saturn",
    11: "Saturn",
    12: "Jupiter",
}


_VIMSHOTTARI_ORDER = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

_VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}


def _angle_sep_deg(a: float, b: float) -> float:
    """Return the minimum absolute angular separation between two longitudes (degrees)."""
    d = abs((float(a) - float(b)) % 360.0)
    return d if d <= 180.0 else 360.0 - d


def _nakshatra_lord_from_lon(lon: float) -> str:
    # Lords repeat every 9 nakshatras.
    segment = 360.0 / 27.0
    idx0 = int((float(lon) % 360.0) / segment)
    return _VIMSHOTTARI_ORDER[idx0 % 9]


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

# Vedic naming syllables by nakshatra (4 padas each). Used for “name alphabet”.
_NAKSHATRA_PADA_SYLLABLES = {
    "Ashwini": ["Chu", "Che", "Cho", "La"],
    "Bharani": ["Li", "Lu", "Le", "Lo"],
    "Krittika": ["A", "E", "U", "Ea"],
    "Rohini": ["O", "Va", "Vi", "Vu"],
    "Mrigashirsha": ["Ve", "Vo", "Ka", "Ki"],
    "Ardra": ["Ku", "Gha", "Na", "Cha"],
    "Punarvasu": ["Ke", "Ko", "Ha", "Hi"],
    "Pushya": ["Hu", "He", "Ho", "Da"],
    "Ashlesha": ["Di", "Du", "De", "Do"],
    "Magha": ["Ma", "Mi", "Mu", "Me"],
    "Purva Phalguni": ["Mo", "Ta", "Ti", "Tu"],
    "Uttara Phalguni": ["Te", "To", "Pa", "Pi"],
    "Hasta": ["Pu", "Sha", "Na", "Tha"],
    "Chitra": ["Pe", "Po", "Ra", "Ri"],
    "Swati": ["Ru", "Re", "Ro", "Ta"],
    "Vishakha": ["Ti", "Tu", "Te", "To"],
    "Anuradha": ["Na", "Ni", "Nu", "Ne"],
    "Jyeshtha": ["No", "Ya", "Yi", "Yu"],
    "Mula": ["Ye", "Yo", "Bha", "Bhi"],
    "Purva Ashadha": ["Bhu", "Dha", "Pha", "Dha"],
    "Uttara Ashadha": ["Bhe", "Bho", "Ja", "Ji"],
    "Shravana": ["Ju", "Je", "Jo", "Gha"],
    "Dhanishta": ["Ga", "Gi", "Gu", "Ge"],
    "Shatabhisha": ["Go", "Sa", "Si", "Su"],
    "Purva Bhadrapada": ["Se", "So", "Da", "Di"],
    "Uttara Bhadrapada": ["Du", "Tha", "Jha", "Na"],
    "Revati": ["De", "Do", "Cha", "Chi"],
}


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


_GANA_BY_NAKSHATRA = {
    "Ashwini": "Deva",
    "Bharani": "Manushya",
    "Krittika": "Rakshasa",
    "Rohini": "Manushya",
    "Mrigashirsha": "Deva",
    "Ardra": "Manushya",
    "Punarvasu": "Deva",
    "Pushya": "Deva",
    "Ashlesha": "Rakshasa",
    "Magha": "Rakshasa",
    "Purva Phalguni": "Manushya",
    "Uttara Phalguni": "Manushya",
    "Hasta": "Deva",
    "Chitra": "Rakshasa",
    "Swati": "Deva",
    "Vishakha": "Rakshasa",
    "Anuradha": "Deva",
    "Jyeshtha": "Rakshasa",
    "Mula": "Rakshasa",
    "Purva Ashadha": "Manushya",
    "Uttara Ashadha": "Manushya",
    "Shravana": "Deva",
    "Dhanishta": "Rakshasa",
    "Shatabhisha": "Rakshasa",
    "Purva Bhadrapada": "Manushya",
    "Uttara Bhadrapada": "Manushya",
    "Revati": "Deva",
}


# Nakshatra Yoni (animal) mapping.
# Source: Commonly used Yoni Porutham tables (e.g. Astrolaabh yoni chart).
_YONI_BY_NAKSHATRA = {
    "Ashwini": "Horse",
    "Bharani": "Elephant",
    "Krittika": "Sheep",
    "Rohini": "Snake",
    "Mrigashirsha": "Snake",
    "Ardra": "Dog",
    "Punarvasu": "Cat",
    "Pushya": "Goat",
    "Ashlesha": "Cat",
    "Magha": "Rat",
    "Purva Phalguni": "Rat",
    "Uttara Phalguni": "Cow",
    "Hasta": "Buffalo",
    "Chitra": "Tiger",
    "Swati": "Buffalo",
    "Vishakha": "Tiger",
    "Anuradha": "Deer",
    "Jyeshtha": "Deer",
    "Mula": "Dog",
    "Purva Ashadha": "Monkey",
    "Uttara Ashadha": "Mongoose",
    "Shravana": "Monkey",
    "Dhanishta": "Lion",
    "Shatabhisha": "Horse",
    "Purva Bhadrapada": "Lion",
    "Uttara Bhadrapada": "Cow",
    "Revati": "Elephant",
}

# Sanskrit/Hindi-style yoni labels used by many Kundli UIs.
# (Example: Pushya -> Chaga, where English table often says Goat.)
_YONI_SANSKRIT_BY_NAKSHATRA = {
    "Ashwini": "Ashwa",
    "Bharani": "Gaja",
    "Krittika": "Mesha",
    "Rohini": "Sarpa",
    "Mrigashirsha": "Sarpa",
    "Ardra": "Shwan",
    "Punarvasu": "Marjara",
    "Pushya": "Chaga",
    "Ashlesha": "Marjara",
    "Magha": "Mushaka",
    "Purva Phalguni": "Mushaka",
    "Uttara Phalguni": "Gau",
    "Hasta": "Mahisha",
    "Chitra": "Vyaghra",
    "Swati": "Mahisha",
    "Vishakha": "Vyaghra",
    "Anuradha": "Mriga",
    "Jyeshtha": "Mriga",
    "Mula": "Shwan",
    "Purva Ashadha": "Vanara",
    "Uttara Ashadha": "Nakula",
    "Shravana": "Vanara",
    "Dhanishta": "Simha",
    "Shatabhisha": "Ashwa",
    "Purva Bhadrapada": "Simha",
    "Uttara Bhadrapada": "Gau",
    "Revati": "Gaja",
}


def _nadi_from_nakshatra_index(nak_index_1_based: int) -> str:
    # Standard repeating nadi pattern: Aadi, Madhya, Antya
    mod = (nak_index_1_based - 1) % 3
    return ["Aadi", "Madhya", "Antya"][mod]


def _paya_from_moon_house(lagna_rashi: int, moon_rashi: int) -> tuple[str, int]:
    """Return (label, moon_house).

    Uses whole-sign house counting from Lagna to Moon rashi:
      1/6/11 -> Swarna (Gold)
      2/5/9  -> Rajat (Silver)
      3/7/10 -> Tamra (Copper)
      4/8/12 -> Loha (Iron)
    """

    moon_house = ((int(moon_rashi) - int(lagna_rashi)) % 12) + 1
    if moon_house in (1, 6, 11):
        return "Swarna (Gold)", moon_house
    if moon_house in (2, 5, 9):
        return "Rajat (Silver)", moon_house
    if moon_house in (3, 7, 10):
        return "Tamra (Copper)", moon_house
    return "Loha (Iron)", moon_house

def calculate_complete_kundli(dob, tob, lat, lon):
    dt_local_naive = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")

    # Use a fixed-offset timezone for IST (GMT+5.5) instead of region tz names.
    # This avoids Asia/Kolkata naming and keeps output consistent.
    tz_name = "GMT+5.5"
    tz_obj = timezone(timedelta(hours=5, minutes=30))
    dt_local = dt_local_naive.replace(tzinfo=tz_obj)
    dt_utc = dt_local.astimezone(timezone.utc)

    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    # Ayanamsha (Lahiri) at UT
    try:
        ayanamsha = float(swe.get_ayanamsa_ut(jd))
    except Exception:
        ayanamsha = None

    # 1. Calculate Lagna (Ascendant)
    # 'B' stands for Alcabitius house system, often used for Vedic compatibility in swe
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b'B', swe.FLG_SIDEREAL)
    lagna_deg = ascmc[0]
    lagna_rashi = int(lagna_deg / 30) + 1
    
    # 2. Planetary Positions
    # Swiss Ephemeris planet indices: 0..9 (Su..Pl), 10 mean node, 11 true node.
    # For Vedic-style charts we include nodes and (optionally) outer planets.
    rahu_id = getattr(swe, "TRUE_NODE", 11)
    planets_map = {
        "Sun": 0,
        "Moon": 1,
        "Mars": 4,
        "Mercury": 2,
        "Jupiter": 5,
        "Venus": 3,
        "Saturn": 6,
        "Uranus": 7,
        "Neptune": 8,
        "Pluto": 9,
        "Rahu": rahu_id,
    }

    planet_data = []

    sun_lon_for_combust = None
    
    # Typical combustion orbs (degrees). Different traditions vary; keep it lightweight.
    combust_orb = {
        "Mercury": 14.0,
        "Venus": 10.0,
        "Mars": 17.0,
        "Jupiter": 11.0,
        "Saturn": 15.0,
    }

    def _append_body(name: str, body_lon: float, speed_lon: float | None = None):
        body_lon = float(body_lon) % 360.0
        rashi = int(body_lon / 30.0) + 1
        deg_in_sign = body_lon % 30.0

        nak_name_p, nak_pada_p, _ = _nakshatra_from_lon(body_lon)
        nak_lord = _nakshatra_lord_from_lon(body_lon)
        sign_name = _RASHI_NAMES.get(rashi, "—")
        sign_lord = _RASHI_LORD.get(rashi, "—")

        lagna_rashi_i = int(lagna_rashi) if lagna_rashi else None
        house = ((int(rashi) - int(lagna_rashi_i)) % 12) + 1 if lagna_rashi_i else None

        retro = bool(speed_lon is not None and float(speed_lon) < 0.0)
        combust = False
        if sun_lon_for_combust is not None and name in combust_orb:
            combust = _angle_sep_deg(body_lon, float(sun_lon_for_combust)) <= combust_orb[name]

        planet_data.append(
            {
                "name": name,
                "lon": round(body_lon, 6),
                "deg": round(deg_in_sign, 2),
                "rashi": rashi,
                "sign": sign_name,
                "sign_lord": sign_lord,
                "nakshatra": nak_name_p,
                "nakshatra_pada": nak_pada_p,
                "nakshatra_lord": nak_lord,
                "house": house,
                "retro": retro,
                "combust": combust,
            }
        )

    # Add Ascendant as a pseudo-body so the frontend can render it like the reference chart.
    _append_body("Asc", lagna_deg, None)

    rahu_speed_lon = None

    for name, body_id in planets_map.items():
        # Request speed so we can mark retrograde correctly.
        res, _ = swe.calc_ut(jd, body_id, int(swe.FLG_SIDEREAL) | int(getattr(swe, "FLG_SPEED", 0)))
        # res[3] is speed in longitude for most bodies in Swiss Ephemeris.
        speed_lon = None
        try:
            speed_lon = float(res[3])
        except Exception:
            speed_lon = None

        if name == "Sun":
            sun_lon_for_combust = float(res[0])

        if name == "Rahu":
            rahu_speed_lon = speed_lon

        _append_body(name, res[0], speed_lon)

    # Ketu is always 180° opposite Rahu.
    rahu_lon = next(p["lon"] for p in planet_data if p["name"] == "Rahu")
    # Ketu is opposite Rahu; use Rahu speed for Retro(R) parity.
    _append_body("Ketu", (rahu_lon + 180.0) % 360.0, rahu_speed_lon)

    # 3. Panchang (basic tithi)
    sun_lon = next(p["lon"] for p in planet_data if p["name"] == "Sun")
    moon_lon = next(p["lon"] for p in planet_data if p["name"] == "Moon")
    elongation = (moon_lon - sun_lon) % 360.0
    tithi_num = int(elongation / 12.0) + 1  # 1..30

    shukla_names = [
        "Pratipada",
        "Dwitiya",
        "Tritiya",
        "Chaturthi",
        "Panchami",
        "Shashthi",
        "Saptami",
        "Ashtami",
        "Navami",
        "Dashami",
        "Ekadashi",
        "Dwadashi",
        "Trayodashi",
        "Chaturdashi",
        "Purnima",
    ]
    krishna_names = shukla_names[:-1] + ["Amavasya"]

    if 1 <= tithi_num <= 15:
        tithi_name = f"Shukla {shukla_names[tithi_num - 1]} ({tithi_num})"
    else:
        idx = tithi_num - 16
        tithi_name = f"Krishna {krishna_names[idx]} ({tithi_num})"

    karan_name = _karana_from_elongation(elongation)
    yoga_name = _yoga_from_sun_moon(sun_lon, moon_lon)

    nak_name, nak_pada, name_alphabet = _nakshatra_from_lon(moon_lon)
    nak_charan = f"{nak_name} (Pada {nak_pada})"

    sunrise, sunset = _calc_sunrise_sunset(dob, tz_obj, float(lat), float(lon))

    moon_rashi = int(moon_lon / 30.0) + 1
    sign_name = _RASHI_NAMES.get(moon_rashi, "—")
    sign_lord = _RASHI_LORD.get(moon_rashi, "—")

    varna = _varna_from_rashi(moon_rashi)
    vashya = _vashya_from_rashi(moon_rashi)
    yoni = _YONI_SANSKRIT_BY_NAKSHATRA.get(nak_name) or _YONI_BY_NAKSHATRA.get(nak_name, "—")
    yoni_english = _YONI_BY_NAKSHATRA.get(nak_name, "—")
    gan = _GANA_BY_NAKSHATRA.get(nak_name, "—")
    nadi = _nadi_from_nakshatra_index(_NAKSHATRA_NAMES.index(nak_name) + 1)
    paya, moon_house = _paya_from_moon_house(lagna_rashi, moon_rashi)

    # Very lightweight “avakhada-like” summary. (Tables like yoni/gan/nadi vary by tradition;
    # leaving them optional until you want strict table parity.)
    avakhada = {
        "varna": varna,
        "vashya": vashya,
        "yoni": yoni,
        "yoni_english": yoni_english,
        "gan": gan,
        "nadi": nadi,
        "sign": sign_name,
        "sign_lord": sign_lord,
        "nakshatra_charan": nak_charan,
        "yog": yoga_name,
        "karan": karan_name,
        "tithi": tithi_name,
        "paya": paya,
        "moon_house": moon_house,
        "name_alphabet": name_alphabet,
    }

    # Vimshottari Mahadasha list (starts from Birth, first entry is partial remainder)
    dasha = _calc_vimshottari_mahadasha(dob, tob, moon_lon)

    return {
        "planets": planet_data,
        "panchang": {
            "lagna": round(lagna_deg, 2),
            "lagna_rashi": lagna_rashi,
            "lat": float(lat),
            "lon": float(lon),
            "tz": tz_name,
            "tithi": tithi_name,
            "tithi_num": tithi_num,
            "karan": karan_name,
            "yog": yoga_name,
            "nakshatra": nak_name,
            "sunrise": sunrise,
            "sunset": sunset,
            "ayanamsha": ayanamsha,
        },
        "avakhada": avakhada,
        "dasha": dasha,
    }