from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class KundliRecord(Base):
    __tablename__ = "kundli_records"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    dob = Column(String, nullable=False)
    tob = Column(String, nullable=False)
    place = Column(String, nullable=False)

    panchang = Column(JSON, nullable=False)
    planets = Column(JSON, nullable=False)
    avakhada = Column(JSON, nullable=True)
    dasha = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
