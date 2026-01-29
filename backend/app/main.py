from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from . import models, database, astrology
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
        conn.execute(text("ALTER TABLE kundli_records ADD COLUMN IF NOT EXISTS avakhada JSON"))
except Exception:
    # Non-fatal: if this fails, new DBs will still have the column via models.py.
    pass

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
            panchang=results['panchang'],
            planets=results['planets'],
            avakhada=results.get('avakhada'),
            dasha=results['dasha']
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
        payload.append(
            {
                "id": r.id,
                "full_name": r.full_name,
                "gender": getattr(r, "gender", None),
                "dob": r.dob,
                "tob": r.tob,
                "place": r.place,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "panchang": r.panchang,
                "planets": r.planets,
                "avakhada": getattr(r, "avakhada", None),
                "dasha": r.dasha,
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
        return astrology.calc_vimshottari_subperiods(
            req.parent_planet,
            req.start_date,
            req.end_date,
            parent_total_years=req.parent_total_years,
            offset_years=req.offset_years or 0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))