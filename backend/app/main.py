from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware
from . import models, database, astrology
from .dasha_logic import calc_vimshottari_subperiods
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from urllib.parse import quote
from urllib.request import Request, urlopen
import json

# Create DB tables
models.Base.metadata.create_all(bind=database.engine)

# Best-effort schema migration for existing databases.
# (SQLAlchemy create_all does not add new columns to existing tables.)
try:
    with database.engine.begin() as conn:
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS gender VARCHAR"))
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION"))
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


def geocode_place(place: str) -> tuple[float, float] | None:
    # Nominatim usage policy asks for a valid User-Agent identifying your app.
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={quote(place)}"
    req = Request(url, headers={"User-Agent": "KundliHub/1.0 (local dev)"})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None

@app.post("/generate")
def generate_kundli_api(request: KundliRequest, db: Session = Depends(database.get_db)):
    # 1. Perform Calculations
    try:
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

        results = astrology.calculate_complete_kundli(
            request.dob, request.tob, lat, lon
        )
        
        # 2. Save to Neon DB
        new_record = models.KundliRecord(
            full_name=request.full_name,
            gender=request.gender,
            dob=request.dob,
            tob=request.tob,
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

        return astrology.calculate_complete_kundli(request.dob, request.tob, lat, lon)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(limit: int = 25, db: Session = Depends(database.get_db)):
    limit = max(1, min(int(limit), 200))
    records = (
        db.query(models.KundliRecord)
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
                "dasha": dasha,
            }
        )

    return jsonable_encoder(payload)


@app.delete("/history/{record_id}")
def delete_history_item(record_id: int, db: Session = Depends(database.get_db)):
    record = db.query(models.KundliRecord).filter(models.KundliRecord.id == record_id).first()
    if not record:
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