from __future__ import annotations
from typing import Any

# Major planets used for Kalsarpa and Aspect checks
_MAJOR_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")

def _norm360(x: float) -> float:
    """Normalizes any angle to 0-360 degrees."""
    return float(x) % 360.0 if x is not None else 0.0

def _between_circular(start: float, end: float, x: float) -> bool:
    """Checks if angle x is within the arc from start to end (clockwise)."""
    start, end, x = _norm360(start), _norm360(end), _norm360(x)
    if start <= end:
        return start <= x <= end
    return x >= start or x <= end

def _get_aspect_diffs(h1: int, h2: int) -> int:
    """Returns the house distance (count) between two houses."""
    return (h1 - h2) % 12

def _ordinal_word(n: int) -> str:
    return {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
            7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}.get(int(n), f"{int(n)}th")

def calc_kalsarpa_dosha(planets: list[dict[str, Any]] | None) -> dict[str, Any]:
    """
    Calculates Kalsarpa Dosha based on the strict longitudinal arc.
    Standard: All 7 major planets must be within the Rahu-Ketu axis.
    """
    idx = {str(p.get("name")): p for p in (planets or []) if p.get("name")}
    rahu, ketu = idx.get("Rahu"), idx.get("Ketu")
    
    if not rahu or not ketu:
        return {"present": None, "note": "Rahu/Ketu coordinates missing"}

    r_lon, k_lon = _norm360(rahu.get("lon")), _norm360(ketu.get("lon"))
    
    # Filter for the 7 major planets (Sun through Saturn)
    planets_to_check = [p for p in planets if p.get("name") in _MAJOR_PLANETS]
    total_planets = len(planets_to_check)
    
    if total_planets < 7:
        return {"present": None, "note": "Insufficient planetary data for Kalsarpa check"}

    # Identify which planets fall into which side of the nodal axis
    in_arc_1 = [p["name"] for p in planets_to_check if _between_circular(r_lon, k_lon, p["lon"])]
    in_arc_2 = [p["name"] for p in planets_to_check if _between_circular(k_lon, r_lon, p["lon"])]
    
    is_full = (len(in_arc_1) == total_planets or len(in_arc_2) == total_planets)
    is_partial = False
    outside_planets = []

    if not is_full:
        # Ardh (Partial) Kalsarpa occurs if only one planet peeks out of the axis
        if len(in_arc_1) == total_planets - 1:
            is_partial = True
            outside_planets = [p["name"] for p in planets_to_check if p["name"] not in in_arc_1]
        elif len(in_arc_2) == total_planets - 1:
            is_partial = True
            outside_planets = [p["name"] for p in planets_to_check if p["name"] not in in_arc_2]

    # Map the type based on Rahu's house position
    k_types = {1: "Anant", 2: "Kulik", 3: "Vasuki", 4: "Shankhapal", 5: "Padma", 
               6: "Mahapadma", 7: "Takshak", 8: "Karkotak", 9: "Shankachood", 
               10: "Ghatak", 11: "Vishdhar", 12: "Sheshnag"}
    
    r_house = int(rahu.get("house", 0))
    current_type = k_types.get(r_house, "Unknown")

    return {
        "present": is_full,
        "is_partial": is_partial,
        "type": current_type if (is_full or is_partial) else None,
        "outside_planets": outside_planets,
        "reason": f"Full {current_type} Kalsarpa" if is_full else (f"Partial {current_type} (Ardh) Kalsarpa" if is_partial else "No Kalsarpa detected"),
        "note": "Calculation based on strict longitudinal nodal arc."
    }

def calc_manglik_dosha(planets: list[dict[str, Any]] | None) -> dict[str, Any]:
    """
    Calculates Manglik Dosha using both North and South Indian house rules
    and applies standard Vedic cancellations (Bhanga).
    """
    idx = {str(p.get("name")): p for p in (planets or []) if p.get("name")}
    mars = idx.get("Mars")
    
    if not mars:
        return {"present": None, "note": "Mars data missing"}

    m_house = int(mars.get("house", 0))
    m_rashi = int(mars.get("rashi", 0))
    
    # 1, 4, 7, 8, 12 are North Indian standard. 2 is added for South Indian/Standard precision.
    trigger_houses = [1, 2, 4, 7, 8, 12]
    is_manglik = m_house in trigger_houses
    cancellation_reasons = []

    if is_manglik:
        # 1. Sign-based Cancellations (Ruchaka Yoga & Strength)
        if m_rashi in [1, 8]: # Aries, Scorpio (Own signs)
            is_manglik = False
            cancellation_reasons.append("Mars is in its own sign (Aries/Scorpio).")
        elif m_rashi == 10: # Capricorn (Exaltation)
            is_manglik = False
            cancellation_reasons.append("Mars is exalted in Capricorn.")
        
        # 2. Jupiter Neutralization (Aspect/Conjunction)
        jupiter = idx.get("Jupiter")
        if jupiter:
            j_house = int(jupiter.get("house", 0))
            # Jupiter aspects: 1 (conjunct), 5, 7, 9
            j_diff = _get_aspect_diffs(m_house, j_house)
            if j_diff in [0, 4, 6, 8]:
                is_manglik = False
                cancellation_reasons.append("Benefic Jupiter aspects or is conjunct with Mars.")

        # 3. Saturn Neutralization (Cooling effect)
        saturn = idx.get("Saturn")
        if saturn:
            s_house = int(saturn.get("house", 0))
            # Saturn aspects: 1 (conjunct), 3, 7, 10
            s_diff = _get_aspect_diffs(m_house, s_house)
            if s_diff in [0, 2, 6, 9]:
                is_manglik = False
                cancellation_reasons.append("Saturn's cold aspect neutralizes Mars's heat.")

        # 4. Sign-House Specific Exceptions
        if (m_house == 4 and m_rashi == 8) or (m_house == 7 and m_rashi == 10):
            is_manglik = False
            cancellation_reasons.append("Special house-sign combination neutralization.")

    return {
        "present": is_manglik,
        "mars_house": m_house,
        "cancellation_reasons": cancellation_reasons,
        "reason": f"Manglik in {_ordinal_word(m_house)} house" if is_manglik else "Non-Manglik / Cancelled",
        "traditions": {
            "north_indian": "Checked 1, 4, 7, 8, 12 houses.",
            "south_indian": "Includes 2nd house (Standard South/Keralite tradition)."
        }
    }

def calculate_doshas(*, planets: list[dict[str, Any]] | None, avakhada: dict[str, Any] | None) -> dict[str, Any]:
    """Entry point for all Dosha calculations."""
    return {
        "kalsarpa": calc_kalsarpa_dosha(planets),
        "manglik": calc_manglik_dosha(planets),
    }