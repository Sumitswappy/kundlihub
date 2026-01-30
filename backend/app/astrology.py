import swisseph as swe
from datetime import datetime, timezone, timedelta

from .constants import (
    _GANA_BY_NAKSHATRA,
    _NAKSHATRA_NAMES,
    _RASHI_LORD,
    _RASHI_NAMES,
    _YONI_BY_NAKSHATRA,
    _YONI_SANSKRIT_BY_NAKSHATRA,
)
from .dasha_logic import _calc_vimshottari_mahadasha
from .panchang_logic import (
    _calc_sunrise_sunset,
    _karana_from_elongation,
    _nakshatra_from_lon,
    _nakshatra_lord_from_lon,
    _nadi_from_nakshatra_index,
    _paya_from_moon_house,
    _paya_from_nakshatra,
    _varna_from_rashi,
    _vashya_from_rashi,
    _yoga_from_sun_moon,
)
from .utils import _angle_sep_deg

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
    paya_house, moon_house = _paya_from_moon_house(lagna_rashi, moon_rashi)
    paya_nakshatra = _paya_from_nakshatra(nak_name)

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
        # Keep `paya` for backwards compatibility; prefer nakshatra-based paya.
        "paya": paya_nakshatra,
        "paya_nakshatra": paya_nakshatra,
        "paya_moon_house": paya_house,
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