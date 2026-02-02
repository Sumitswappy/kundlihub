from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
from . import models, database, astrology
from . import auth
from .dasha_logic import calc_vimshottari_subperiods
from .dosha_logic import calculate_doshas
from .horoscope_logic import calculate_daily_horoscope
from .sadesati_logic import calculate_sade_sati
from .sadesati_logic import build_sade_sati_timeline
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
import os
import calendar
import time
from datetime import date
from datetime import datetime, timedelta, timezone

# Create DB tables
models.Base.metadata.create_all(bind=database.engine)

# Best-effort schema migration for existing databases.
# (SQLAlchemy create_all does not add new columns to existing tables.)
try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS gender VARCHAR"))
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS user_id INTEGER"))
except Exception:
    # Non-fatal: if this fails, new DBs will still have the column via models.py.
    pass


def _coerce_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def _migrate_legacy_json_to_normalized_if_present() -> None:
    """Best-effort migration for older rows created before normalization.

    If kundli_records still has JSON columns, copy their content into the normalized tables
    (only when missing), then we can safely drop the JSON columns.
    """

    try:
        insp = inspect(database.engine)
        cols = {c["name"] for c in insp.get_columns("kundli_records")}
    except Exception:
        return

    legacy_cols = {"panchang", "planets", "avakhada", "dasha"}
    if not legacy_cols.issubset(cols):
        return

    db = database.SessionLocal()
    try:
        rows = (
            db.execute(
                text(
                    "SELECT id, panchang, planets, avakhada, dasha FROM kundli_records "
                    "ORDER BY id DESC"
                )
            )
            .mappings()
            .all()
        )

        for r in rows:
            record_id = int(r["id"])

            # Panchang 1:1
            exists = db.execute(
                text("SELECT 1 FROM kundli_panchang WHERE record_id = :id"), {"id": record_id}
            ).first()
            if not exists:
                p = _coerce_json(r["panchang"]) or {}
                db.add(
                    models.KundliPanchang(
                        record_id=record_id,
                        lagna=p.get("lagna"),
                        lagna_rashi=p.get("lagna_rashi"),
                        lat=p.get("lat"),
                        lon=p.get("lon"),
                        tz=p.get("tz"),
                        tithi=p.get("tithi"),
                        tithi_num=p.get("tithi_num"),
                        karan=p.get("karan"),
                        yog=p.get("yog"),
                        nakshatra=p.get("nakshatra"),
                        sunrise=p.get("sunrise"),
                        sunset=p.get("sunset"),
                        ayanamsha=p.get("ayanamsha"),
                    )
                )

            # Avakhada 1:1
            exists = db.execute(
                text("SELECT 1 FROM kundli_avakhada WHERE record_id = :id"), {"id": record_id}
            ).first()
            a = _coerce_json(r["avakhada"]) or {}
            if not exists and a:
                db.add(
                    models.KundliAvakhada(
                        record_id=record_id,
                        varna=a.get("varna"),
                        vashya=a.get("vashya"),
                        yoni=a.get("yoni"),
                        yoni_english=a.get("yoni_english"),
                        gan=a.get("gan"),
                        nadi=a.get("nadi"),
                        sign=a.get("sign"),
                        sign_lord=a.get("sign_lord"),
                        nakshatra_charan=a.get("nakshatra_charan"),
                        yog=a.get("yog"),
                        karan=a.get("karan"),
                        tithi=a.get("tithi"),
                        paya=a.get("paya"),
                        paya_nakshatra=a.get("paya_nakshatra"),
                        paya_moon_house=a.get("paya_moon_house"),
                        moon_house=a.get("moon_house"),
                        name_alphabet=a.get("name_alphabet"),
                    )
                )

            # Planets 1:N
            exists = db.execute(
                text("SELECT 1 FROM kundli_planets WHERE record_id = :id LIMIT 1"),
                {"id": record_id},
            ).first()
            if not exists:
                for pl in _coerce_json(r["planets"]) or []:
                    db.add(
                        models.KundliPlanet(
                            record_id=record_id,
                            name=pl.get("name"),
                            lon=pl.get("lon"),
                            deg=pl.get("deg"),
                            rashi=pl.get("rashi"),
                            sign=pl.get("sign"),
                            sign_lord=pl.get("sign_lord"),
                            nakshatra=pl.get("nakshatra"),
                            nakshatra_pada=pl.get("nakshatra_pada"),
                            nakshatra_lord=pl.get("nakshatra_lord"),
                            house=pl.get("house"),
                            retro=pl.get("retro"),
                            combust=pl.get("combust"),
                        )
                    )

            # Dasha periods 1:N
            exists = db.execute(
                text("SELECT 1 FROM kundli_dasha_periods WHERE record_id = :id LIMIT 1"),
                {"id": record_id},
            ).first()
            if not exists:
                for i, row in enumerate(_coerce_json(r["dasha"]) or []):
                    db.add(
                        models.KundliDashaPeriod(
                            record_id=record_id,
                            level="mahadasha",
                            seq=i,
                            planet=row.get("planet"),
                            start_date=row.get("start_date"),
                            end_date=row.get("end_date"),
                            start_label=row.get("start_label"),
                            years=row.get("years"),
                            total_years=row.get("total_years"),
                            offset_years=row.get("offset_years"),
                        )
                    )

        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def _drop_legacy_json_columns_best_effort() -> None:
    # NOTE: SQLite can't reliably DROP COLUMN without table rebuild; we skip there.
    try:
        if database.engine.dialect.name.startswith("sqlite"):
            return
    except Exception:
        return

    try:
        with database.engine.begin() as conn:
            conn.execute(text("ALTER TABLE kundli_records DROP COLUMN IF EXISTS panchang"))
            conn.execute(text("ALTER TABLE kundli_records DROP COLUMN IF EXISTS planets"))
            conn.execute(text("ALTER TABLE kundli_records DROP COLUMN IF EXISTS avakhada"))
            conn.execute(text("ALTER TABLE kundli_records DROP COLUMN IF EXISTS dasha"))
    except Exception:
        # Non-fatal: if it fails, app can still run.
        pass


_migrate_legacy_json_to_normalized_if_present()
_drop_legacy_json_columns_best_effort()

app = FastAPI()

security = HTTPBearer(auto_error=False)

# Enable CORS for Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

class KundliRequest(BaseModel):
    full_name: str
    gender: str | None = None
    dob: str  # YYYY-MM-DD
    tob: str  # HH:MM
    place: str
    lat: float | None = None
    lon: float | None = None


class DashaSubperiodsRequest(BaseModel):
    parent_planet: str
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    parent_total_years: float
    offset_years: float | None = 0.0


class DailyHoroscopeRequest(KundliRequest):
    for_date: str | None = None  # YYYY-MM-DD (optional)


class SadeSatiRequest(KundliRequest):
    for_date: str | None = None  # YYYY-MM-DD (optional)


class RequestOtpBody(BaseModel):
    email: str


class VerifyOtpBody(BaseModel):
    email: str
    otp: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _add_years_safe(d: date, years: int) -> date:
    """Add years while keeping month/day valid (Feb 29 -> Feb 28 for non-leap years)."""
    y = int(d.year) + int(years)
    last_day = calendar.monthrange(y, d.month)[1]
    day = min(int(d.day), int(last_day))
    return date(y, d.month, day)


def _normalize_dob(dob: str) -> str:
    """Normalize a date-of-birth string to ISO (YYYY-MM-DD).

    Frontends sometimes send DD-MM-YYYY or DD/MM/YYYY; astrology + panchang code
    expects YYYY-MM-DD.
    """

    dob_s = (str(dob) if dob is not None else "").strip()
    if not dob_s:
        raise HTTPException(status_code=422, detail="dob is required")

    try:
        return date.fromisoformat(dob_s).isoformat()
    except Exception:
        pass

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(dob_s, fmt).date().isoformat()
        except Exception:
            continue

    raise HTTPException(status_code=422, detail="Invalid dob; expected YYYY-MM-DD")


def _normalize_tob(tob: str) -> str:
    """Normalize a time-of-birth string to HH:MM (24h)."""

    tob_s = (str(tob) if tob is not None else "").strip()
    if not tob_s:
        raise HTTPException(status_code=422, detail="tob is required")

    # Common case: browser <input type="time"> may send HH:MM or HH:MM:SS
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(tob_s, fmt)
            return parsed.strftime("%H:%M")
        except Exception:
            continue

    raise HTTPException(status_code=422, detail="Invalid tob; expected HH:MM")


def _kundli_stub_from_record(record: models.KundliRecord) -> dict:
    """Build the minimal kundli dict needed for Sade Sati (Moon rashi)."""
    planets = []
    for pl in getattr(record, "planet_rows", []) or []:
        planets.append({"name": pl.name, "rashi": pl.rashi})
    return {"planets": planets}


def get_current_user(
    db: Session = Depends(database.get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> models.User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        payload = auth.decode_access_token(creds.credentials)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.post("/auth/request-otp")
def request_otp(body: RequestOtpBody, db: Session = Depends(database.get_db)):
    try:
        email = auth.normalize_email(body.email)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid email")

    # Rate limit OTP generation per email.
    # Default: max 10 OTP requests per 24 hours (configurable via env vars).
    max_requests = int(os.getenv("OTP_MAX_REQUESTS_PER_EMAIL", "10"))
    window_minutes = int(os.getenv("OTP_REQUEST_WINDOW_MINUTES", "1440"))
    window_start = _utcnow() - timedelta(minutes=window_minutes)

    recent_q = db.query(models.EmailOtp).filter(
        models.EmailOtp.email == email,
        models.EmailOtp.created_at >= window_start,
    )
    recent_count = int(recent_q.count())
    if recent_count >= max_requests:
        oldest = recent_q.order_by(models.EmailOtp.created_at.asc()).first()
        retry_after_seconds = 0
        if oldest is not None and oldest.created_at is not None:
            oldest_created_at = oldest.created_at
            if getattr(oldest_created_at, "tzinfo", None) is None:
                oldest_created_at = oldest_created_at.replace(tzinfo=timezone.utc)
            reset_at = oldest_created_at + timedelta(minutes=window_minutes)
            retry_after_seconds = max(1, int((reset_at - _utcnow()).total_seconds()))

        headers = {"Retry-After": str(retry_after_seconds)} if retry_after_seconds else None
        raise HTTPException(
            status_code=429,
            detail="OTP request limit reached for this email. Please try again later.",
            headers=headers,
        )

    ttl_minutes = int(os.getenv("OTP_TTL_MINUTES", "10"))
    otp = auth.generate_otp(6)
    otp_row = models.EmailOtp(
        email=email,
        otp_hash=auth.hash_otp(email, otp),
        expires_at=_utcnow() + timedelta(minutes=ttl_minutes),
        attempts=0,
    )

    db.add(otp_row)
    db.commit()

    try:
        auth.send_login_otp_email(to_email=email, otp=otp, ttl_minutes=ttl_minutes)
    except Exception as e:
        try:
            db.delete(otp_row)
            db.commit()
        except Exception:
            # Best-effort cleanup only.
            pass
        # Keep response generic.
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")

    # In DEV_OTP_ECHO mode, the OTP is printed server-side.
    return {"ok": True}


@app.post("/auth/verify-otp")
def verify_otp(body: VerifyOtpBody, db: Session = Depends(database.get_db)):
    try:
        email = auth.normalize_email(body.email)
        otp = (body.otp or "").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid email or OTP")

    row = (
        db.query(models.EmailOtp)
        .filter(models.EmailOtp.email == email)
        .order_by(models.EmailOtp.id.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if row.consumed_at is not None:
        raise HTTPException(status_code=400, detail="OTP already used")

    if row.expires_at is None or row.expires_at < _utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    row.attempts = int(row.attempts or 0) + 1
    if row.attempts > int(os.getenv("OTP_MAX_ATTEMPTS", "5")):
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts")

    expected = row.otp_hash
    actual = auth.hash_otp(email, otp)
    if not auth.constant_time_equals(expected, actual):
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    row.consumed_at = _utcnow()

    user = db.query(models.User).filter(models.User.email == email).first()
    now = _utcnow()
    if not user:
        user = models.User(email=email, email_verified_at=now, last_login_at=now)
        db.add(user)
        db.flush()  # get id
    else:
        if user.email_verified_at is None:
            user.email_verified_at = now
        user.last_login_at = now

    db.commit()

    token = auth.create_access_token(user_id=int(user.id), email=user.email)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
def me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "email_verified_at": current_user.email_verified_at.isoformat() if current_user.email_verified_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }


def geocode_place(place: str) -> tuple[float, float] | None:
    # Intermittent failures here are usually due to Nominatim rate limits / timeouts.
    # Keep this best-effort and cache results to reduce repeated calls.

    raw = str(place or "")
    norm = " ".join(raw.strip().split())
    if not norm:
        return None

    # Small per-process cache (Render instances are ephemeral; this still helps a lot).
    # Key is lowercased normalized place string.
    cache_key = norm.lower()
    now = time.time()
    cache_ttl = int(os.getenv("GEOCODE_CACHE_TTL_SECONDS", "86400"))
    try:
        cache = geocode_place._cache  # type: ignore[attr-defined]
    except Exception:
        cache = {}
        geocode_place._cache = cache  # type: ignore[attr-defined]

    hit = cache.get(cache_key)
    if hit:
        ts, lat, lon = hit
        if (now - float(ts)) <= float(cache_ttl):
            return float(lat), float(lon)

    ua = os.getenv(
        "NOMINATIM_USER_AGENT",
        "KundliHub/1.0 (geocoder; contact: set NOMINATIM_USER_AGENT)",
    )
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={quote(norm)}"

    # Retry a couple times with tiny backoff to ride out transient 429/5xx/timeouts.
    for attempt, sleep_s in enumerate((0.0, 0.4, 0.9)):
        if sleep_s:
            try:
                time.sleep(sleep_s)
            except Exception:
                pass

        req = Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if not data:
                return None

            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            cache[cache_key] = (now, lat, lon)

            # Keep cache bounded.
            max_items = int(os.getenv("GEOCODE_CACHE_MAX_ITEMS", "2000"))
            if len(cache) > max_items:
                # Drop oldest ~10%.
                try:
                    for k, _v in sorted(cache.items(), key=lambda kv: kv[1][0])[: max(1, max_items // 10)]:
                        cache.pop(k, None)
                except Exception:
                    pass

            return lat, lon
        except Exception:
            # Try again if attempts remain.
            if attempt >= 2:
                return None

    return None


def _resolve_coords(request: KundliRequest) -> tuple[float, float]:
    lat = request.lat
    lon = request.lon

    if lat is None or lon is None:
        coords = geocode_place(request.place)
        if not coords:
            raise HTTPException(status_code=400, detail="Could not geocode place of birth")
        return coords

    # Heuristic: InputForm defaults to Kolkata; override if user entered a different place.
    if request.place and abs(lat - 22.57) < 0.05 and abs(lon - 88.36) < 0.05:
        coords = geocode_place(request.place)
        if coords:
            return coords

    return float(lat), float(lon)


@app.post("/horoscope/daily")
def daily_horoscope_api(
    request: DailyHoroscopeRequest,
    current_user: models.User = Depends(get_current_user),
):
    """Compute a simple daily horoscope plus remedies.

    Uses natal Moon sign and today's Moon transit as the primary signal.
    """
    try:
        dob = _normalize_dob(request.dob)
        tob = _normalize_tob(request.tob)
        lat, lon = _resolve_coords(request)
        kundli = astrology.calculate_complete_kundli(dob, tob, lat, lon)

        if request.for_date:
            try:
                for_dt = date.fromisoformat(str(request.for_date))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid for_date; expected YYYY-MM-DD")
        else:
            # Server-local date is okay because astrology uses a fixed IST offset.
            for_dt = date.today()

        return calculate_daily_horoscope(kundli=kundli, lat=lat, lon=lon, for_date=for_dt)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sade-sati")
def sade_sati_api(
    request: SadeSatiRequest,
    current_user: models.User = Depends(get_current_user),
):
    """Compute Shani Sade Sati phases + remedies based on natal Moon sign."""
    try:
        dob = _normalize_dob(request.dob)
        tob = _normalize_tob(request.tob)
        lat, lon = _resolve_coords(request)
        kundli = astrology.calculate_complete_kundli(dob, tob, lat, lon)

        if request.for_date:
            try:
                for_dt = date.fromisoformat(str(request.for_date))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid for_date; expected YYYY-MM-DD")
        else:
            for_dt = date.today()

        return calculate_sade_sati(kundli=kundli, for_date=for_dt)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
def generate_kundli_api(
    request: KundliRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 1. Perform Calculations
    try:
        dob = _normalize_dob(request.dob)
        tob = _normalize_tob(request.tob)
        lat = request.lat
        lon = request.lon

        # If frontend didn't provide coordinates (or is still using the placeholder Kolkata coords),
        # geocode the place string so calculations match the user's intended location.
        if lat is None or lon is None:
            coords = geocode_place(request.place)
            if not coords:
                raise HTTPException(status_code=400, detail="Could not geocode place of birth")
            lat, lon = coords
        else:
            # Heuristic: InputForm defaults to Kolkata; override if user entered a different place.
            if request.place and abs(lat - 22.57) < 0.05 and abs(lon - 88.36) < 0.05:
                coords = geocode_place(request.place)
                if coords:
                    lat, lon = coords

        results = astrology.calculate_complete_kundli(dob, tob, lat, lon)

        # 2. Save to DB (best-effort). If saving fails, still return the computed kundli.
        try:
            new_record = models.KundliRecord(
                user_id=int(current_user.id),
                full_name=request.full_name,
                gender=request.gender,
                dob=dob,
                tob=tob,
                place=request.place,
                lat=float(lat) if lat is not None else None,
                lon=float(lon) if lon is not None else None,
            )

            # Normalized one-to-one rows
            p = results.get("panchang") or {}
            new_record.panchang_row = models.KundliPanchang(
                lagna=p.get("lagna"),
                lagna_rashi=p.get("lagna_rashi"),
                lat=p.get("lat"),
                lon=p.get("lon"),
                tz=p.get("tz"),
                tithi=p.get("tithi"),
                tithi_num=p.get("tithi_num"),
                karan=p.get("karan"),
                yog=p.get("yog"),
                nakshatra=p.get("nakshatra"),
                sunrise=p.get("sunrise"),
                sunset=p.get("sunset"),
                ayanamsha=p.get("ayanamsha"),
            )

            a = results.get("avakhada") or {}
            new_record.avakhada_row = models.KundliAvakhada(
                varna=a.get("varna"),
                vashya=a.get("vashya"),
                yoni=a.get("yoni"),
                yoni_english=a.get("yoni_english"),
                gan=a.get("gan"),
                nadi=a.get("nadi"),
                sign=a.get("sign"),
                sign_lord=a.get("sign_lord"),
                nakshatra_charan=a.get("nakshatra_charan"),
                yog=a.get("yog"),
                karan=a.get("karan"),
                tithi=a.get("tithi"),
                paya=a.get("paya"),
                paya_nakshatra=a.get("paya_nakshatra"),
                paya_moon_house=a.get("paya_moon_house"),
                moon_house=a.get("moon_house"),
                name_alphabet=a.get("name_alphabet"),
            )

            # Normalized one-to-many rows
            new_record.planet_rows = []
            for pl in results.get("planets") or []:
                new_record.planet_rows.append(
                    models.KundliPlanet(
                        name=pl.get("name"),
                        lon=pl.get("lon"),
                        deg=pl.get("deg"),
                        rashi=pl.get("rashi"),
                        sign=pl.get("sign"),
                        sign_lord=pl.get("sign_lord"),
                        nakshatra=pl.get("nakshatra"),
                        nakshatra_pada=pl.get("nakshatra_pada"),
                        nakshatra_lord=pl.get("nakshatra_lord"),
                        house=pl.get("house"),
                        retro=pl.get("retro"),
                        combust=pl.get("combust"),
                    )
                )

            new_record.dasha_rows = []
            for i, row in enumerate(results.get("dasha") or []):
                new_record.dasha_rows.append(
                    models.KundliDashaPeriod(
                        level="mahadasha",
                        seq=i,
                        planet=row.get("planet"),
                        start_date=row.get("start_date"),
                        end_date=row.get("end_date"),
                        start_label=row.get("start_label"),
                        years=row.get("years"),
                        total_years=row.get("total_years"),
                        offset_years=row.get("offset_years"),
                    )
                )

            db.add(new_record)
            db.commit()
            db.refresh(new_record)

            results["saved"] = True
            results["record_id"] = int(getattr(new_record, "id", 0) or 0) or None
            return results
        except SQLAlchemyError as e:
            try:
                db.rollback()
            except Exception:
                pass
            results["saved"] = False
            results["record_id"] = None
            results["save_error"] = f"{type(e).__name__}: {str(e)}"
            return results
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calculate")
def calculate_kundli_api(request: KundliRequest):
    """Calculate kundli data without saving a DB record.

    Useful for viewing older saved records that were created before certain fields
    (like avakhada) were persisted.
    """
    try:
        dob = _normalize_dob(request.dob)
        tob = _normalize_tob(request.tob)
        lat = request.lat
        lon = request.lon

        if lat is None or lon is None:
            coords = geocode_place(request.place)
            if not coords:
                raise HTTPException(status_code=400, detail="Could not geocode place of birth")
            lat, lon = coords
        else:
            if request.place and abs(lat - 22.57) < 0.05 and abs(lon - 88.36) < 0.05:
                coords = geocode_place(request.place)
                if coords:
                    lat, lon = coords

        return astrology.calculate_complete_kundli(dob, tob, lat, lon)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(
    limit: int = 25,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    limit = max(1, min(int(limit), 200))
    records = (
        db.query(models.KundliRecord)
        .filter(models.KundliRecord.user_id == int(current_user.id))
        .order_by(models.KundliRecord.created_at.desc())
        .limit(limit)
        .all()
    )

    payload = []
    for r in records:
        p = r.panchang_row
        a = r.avakhada_row

        panchang = {
            "lagna": getattr(p, "lagna", None),
            "lagna_rashi": getattr(p, "lagna_rashi", None),
            "lat": getattr(p, "lat", None),
            "lon": getattr(p, "lon", None),
            "tz": getattr(p, "tz", None),
            "tithi": getattr(p, "tithi", None),
            "tithi_num": getattr(p, "tithi_num", None),
            "karan": getattr(p, "karan", None),
            "yog": getattr(p, "yog", None),
            "nakshatra": getattr(p, "nakshatra", None),
            "sunrise": getattr(p, "sunrise", None),
            "sunset": getattr(p, "sunset", None),
            "ayanamsha": getattr(p, "ayanamsha", None),
        }

        planets = []
        for pl in getattr(r, "planet_rows", []) or []:
            planets.append(
                {
                    "name": pl.name,
                    "lon": pl.lon,
                    "deg": pl.deg,
                    "rashi": pl.rashi,
                    "sign": pl.sign,
                    "sign_lord": pl.sign_lord,
                    "nakshatra": pl.nakshatra,
                    "nakshatra_pada": pl.nakshatra_pada,
                    "nakshatra_lord": pl.nakshatra_lord,
                    "house": pl.house,
                    "retro": pl.retro,
                    "combust": pl.combust,
                }
            )

        avakhada = None
        doshas = None
        if a is not None:
            avakhada = {
                "varna": a.varna,
                "vashya": a.vashya,
                "yoni": a.yoni,
                "yoni_english": a.yoni_english,
                "gan": a.gan,
                "nadi": a.nadi,
                "sign": a.sign,
                "sign_lord": a.sign_lord,
                "nakshatra_charan": a.nakshatra_charan,
                "yog": a.yog,
                "karan": a.karan,
                "tithi": a.tithi,
                "paya": a.paya,
                "paya_nakshatra": a.paya_nakshatra,
                "paya_moon_house": a.paya_moon_house,
                "moon_house": a.moon_house,
                "name_alphabet": a.name_alphabet,
            }

            doshas = calculate_doshas(planets=planets, avakhada=avakhada)

        dasha = []
        for d in getattr(r, "dasha_rows", []) or []:
            if getattr(d, "level", "mahadasha") != "mahadasha":
                continue
            dasha.append(
                {
                    "planet": d.planet,
                    "start_date": d.start_date,
                    "end_date": d.end_date,
                    "start_label": d.start_label,
                    "years": d.years,
                    "total_years": d.total_years,
                    "offset_years": d.offset_years,
                }
            )

        payload.append(
            {
                "id": r.id,
                "full_name": r.full_name,
                "gender": getattr(r, "gender", None),
                "dob": r.dob,
                "tob": r.tob,
                "place": r.place,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "panchang": panchang,
                "planets": planets,
                "avakhada": avakhada,
                "doshas": doshas,
                "dasha": dasha,
            }
        )

    return jsonable_encoder(payload)


@app.get("/history/{record_id}/sade-sati-periods")
def get_sade_sati_periods(
    record_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.KundliRecord).filter(models.KundliRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if int(getattr(record, "user_id", 0) or 0) != int(current_user.id):
        # Avoid leaking record existence.
        raise HTTPException(status_code=404, detail="Record not found")

    existing = (
        db.query(models.KundliSadeSatiPeriod)
        .filter(models.KundliSadeSatiPeriod.record_id == int(record_id))
        .order_by(models.KundliSadeSatiPeriod.seq.asc())
        .all()
    )

    if existing:
        return {
            "ok": True,
            "record_id": int(record_id),
            "rows": [
                {
                    "start": r.start_date,
                    "end": r.end_date,
                    "sign_name": r.sign_name,
                    "phase": r.phase,
                    "type": r.phase_label or r.phase,
                }
                for r in existing
            ],
        }

    # Lazily compute & persist from birth.
    try:
        birth_dt = date.fromisoformat(_normalize_dob(str(record.dob)))
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=f"Record has invalid dob; {e.detail}")

    years_ahead = int(os.getenv("SADE_SATI_TIMELINE_YEARS", "100"))
    end_dt = _add_years_safe(birth_dt, years_ahead)

    kundli = _kundli_stub_from_record(record)
    if not (kundli.get("planets") or []):
        # Fallback: legacy record without persisted planets.
        lat = getattr(record, "lat", None)
        lon = getattr(record, "lon", None)
        if lat is None or lon is None:
            coords = geocode_place(str(record.place or ""))
            if not coords:
                raise HTTPException(status_code=400, detail="Could not geocode place for legacy record")
            lat, lon = coords
        kundli = astrology.calculate_complete_kundli(
            _normalize_dob(str(record.dob)),
            _normalize_tob(str(record.tob)),
            float(lat),
            float(lon),
        )

    timeline = build_sade_sati_timeline(kundli=kundli, start=birth_dt, end=end_dt)
    if not timeline.get("ok"):
        raise HTTPException(status_code=400, detail=str(timeline.get("error") or "Failed to build timeline"))

    created_rows = []
    for i, r in enumerate(timeline.get("rows") or []):
        row = models.KundliSadeSatiPeriod(
            record_id=int(record_id),
            start_date=str(r.get("start")),
            end_date=str(r.get("end")),
            sign_name=str(r.get("sign_name") or ""),
            phase=str(r.get("phase") or ""),
            phase_label=str(r.get("type") or ""),
            seq=int(i),
        )
        db.add(row)
        created_rows.append(
            {
                "start": row.start_date,
                "end": row.end_date,
                "sign_name": row.sign_name,
                "phase": row.phase,
                "type": row.phase_label,
            }
        )

    try:
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise

    return {"ok": True, "record_id": int(record_id), "rows": created_rows}


@app.delete("/history/{record_id}")
def delete_history_item(
    record_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = db.query(models.KundliRecord).filter(models.KundliRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if int(getattr(record, "user_id", 0) or 0) != int(current_user.id):
        # Avoid leaking record existence.
        raise HTTPException(status_code=404, detail="Record not found")
    try:
        db.delete(record)
        db.commit()
        return {"ok": True}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dasha/subperiods")
def get_dasha_subperiods(req: DashaSubperiodsRequest):
    try:
        return calc_vimshottari_subperiods(
            req.parent_planet,
            req.start_date,
            req.end_date,
            parent_total_years=req.parent_total_years,
            offset_years=req.offset_years or 0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))