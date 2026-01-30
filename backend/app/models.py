from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class KundliRecord(Base):
    __tablename__ = "kundli_records"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    dob = Column(String, nullable=False)
    tob = Column(String, nullable=False)
    place = Column(String, nullable=False)

    # Birth coordinates are useful to persist for reproducibility.
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Normalized relationships
    panchang_row = relationship(
        "KundliPanchang",
        back_populates="record",
        uselist=False,
        cascade="all, delete-orphan",
    )
    avakhada_row = relationship(
        "KundliAvakhada",
        back_populates="record",
        uselist=False,
        cascade="all, delete-orphan",
    )
    planet_rows = relationship(
        "KundliPlanet",
        back_populates="record",
        order_by="KundliPlanet.id",
        cascade="all, delete-orphan",
    )
    dasha_rows = relationship(
        "KundliDashaPeriod",
        back_populates="record",
        order_by="KundliDashaPeriod.seq",
        cascade="all, delete-orphan",
    )


class KundliPanchang(Base):
    __tablename__ = "kundli_panchang"

    record_id = Column(Integer, ForeignKey("kundli_records.id", ondelete="CASCADE"), primary_key=True)

    lagna = Column(Float, nullable=True)
    lagna_rashi = Column(Integer, nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    tz = Column(String, nullable=True)
    tithi = Column(String, nullable=True)
    tithi_num = Column(Integer, nullable=True)
    karan = Column(String, nullable=True)
    yog = Column(String, nullable=True)
    nakshatra = Column(String, nullable=True)
    sunrise = Column(String, nullable=True)
    sunset = Column(String, nullable=True)
    ayanamsha = Column(Float, nullable=True)

    record = relationship("KundliRecord", back_populates="panchang_row")


class KundliPlanet(Base):
    __tablename__ = "kundli_planets"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("kundli_records.id", ondelete="CASCADE"), index=True, nullable=False)

    name = Column(String, nullable=False)
    lon = Column(Float, nullable=True)
    deg = Column(Float, nullable=True)
    rashi = Column(Integer, nullable=True)
    sign = Column(String, nullable=True)
    sign_lord = Column(String, nullable=True)
    nakshatra = Column(String, nullable=True)
    nakshatra_pada = Column(Integer, nullable=True)
    nakshatra_lord = Column(String, nullable=True)
    house = Column(Integer, nullable=True)
    retro = Column(Boolean, nullable=True)
    combust = Column(Boolean, nullable=True)

    record = relationship("KundliRecord", back_populates="planet_rows")

    __table_args__ = (
        UniqueConstraint("record_id", "name", name="uq_kundli_planets_record_name"),
    )


class KundliAvakhada(Base):
    __tablename__ = "kundli_avakhada"

    record_id = Column(Integer, ForeignKey("kundli_records.id", ondelete="CASCADE"), primary_key=True)

    varna = Column(String, nullable=True)
    vashya = Column(String, nullable=True)
    yoni = Column(String, nullable=True)
    yoni_english = Column(String, nullable=True)
    gan = Column(String, nullable=True)
    nadi = Column(String, nullable=True)
    sign = Column(String, nullable=True)
    sign_lord = Column(String, nullable=True)
    nakshatra_charan = Column(String, nullable=True)
    yog = Column(String, nullable=True)
    karan = Column(String, nullable=True)
    tithi = Column(String, nullable=True)
    paya = Column(String, nullable=True)
    paya_nakshatra = Column(String, nullable=True)
    paya_moon_house = Column(String, nullable=True)
    moon_house = Column(Integer, nullable=True)
    name_alphabet = Column(String, nullable=True)

    record = relationship("KundliRecord", back_populates="avakhada_row")


class KundliDashaPeriod(Base):
    __tablename__ = "kundli_dasha_periods"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("kundli_records.id", ondelete="CASCADE"), index=True, nullable=False)

    level = Column(String, nullable=False, default="mahadasha")
    seq = Column(Integer, nullable=True)
    planet = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    start_label = Column(String, nullable=True)
    years = Column(Float, nullable=True)
    total_years = Column(Float, nullable=True)
    offset_years = Column(Float, nullable=True)

    record = relationship("KundliRecord", back_populates="dasha_rows")
