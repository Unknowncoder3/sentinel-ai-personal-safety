from datetime import datetime

from pydantic import BaseModel, Field


class JourneyCreate(BaseModel):
    device_id: str | None = None
    destination: str = Field(min_length=2, max_length=255)
    start_latitude: float | None = Field(default=None, ge=-90, le=90)
    start_longitude: float | None = Field(default=None, ge=-180, le=180)
    end_latitude: float | None = Field(default=None, ge=-90, le=90)
    end_longitude: float | None = Field(default=None, ge=-180, le=180)
    eta: datetime


class JourneyPointCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_mps: float | None = Field(default=None, ge=0)
    bearing: float | None = Field(default=None, ge=0, le=360)
    battery_level: float | None = Field(default=None, ge=0, le=100)
    recorded_at: datetime | None = None


class JourneyOut(BaseModel):
    id: str
    device_id: str | None
    destination: str
    start_latitude: float | None
    start_longitude: float | None
    end_latitude: float | None
    end_longitude: float | None
    eta: datetime
    status: str
    risk_score: int
    created_at: datetime
    completed_at: datetime | None


class JourneyPointOut(JourneyPointCreate):
    id: str
    journey_id: str
    recorded_at: datetime
