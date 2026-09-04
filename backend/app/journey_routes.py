from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import get_current_user
from .journey_models import Journey, JourneyPoint
from .journey_schemas import JourneyCreate, JourneyOut, JourneyPointCreate, JourneyPointOut
from .models import Device, User
from .risk_engine import calculate_risk

router = APIRouter(prefix="/api/v1/journeys", tags=["journeys"])


def journey_out(item: Journey) -> JourneyOut:
    return JourneyOut(
        id=item.id, device_id=item.device_id, destination=item.destination,
        start_latitude=item.start_latitude, start_longitude=item.start_longitude,
        end_latitude=item.end_latitude, end_longitude=item.end_longitude,
        eta=item.eta, status=item.status, risk_score=item.risk_score,
        created_at=item.created_at, completed_at=item.completed_at,
    )


@router.post("", response_model=JourneyOut, status_code=status.HTTP_201_CREATED)
def create_journey(payload: JourneyCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.device_id:
        device = db.scalar(select(Device).where(Device.id == payload.device_id, Device.owner_id == current_user.id))
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
    journey = Journey(owner_id=current_user.id, **payload.model_dump())
    db.add(journey)
    db.commit()
    db.refresh(journey)
    return journey_out(journey)


@router.get("", response_model=list[JourneyOut])
def list_journeys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Journey).where(Journey.owner_id == current_user.id).order_by(Journey.created_at.desc()).limit(50)).all()
    return [journey_out(item) for item in items]


@router.get("/{journey_id}", response_model=JourneyOut)
def get_journey(journey_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Journey).where(Journey.id == journey_id, Journey.owner_id == current_user.id))
    if not item:
        raise HTTPException(status_code=404, detail="Journey not found")
    return journey_out(item)


@router.post("/{journey_id}/points", response_model=JourneyPointOut, status_code=status.HTTP_201_CREATED)
def add_point(journey_id: str, payload: JourneyPointCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    journey = db.scalar(select(Journey).where(Journey.id == journey_id, Journey.owner_id == current_user.id))
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    if journey.status != "active":
        raise HTTPException(status_code=409, detail="Journey is not active")

    point = JourneyPoint(journey_id=journey.id, recorded_at=payload.recorded_at or datetime.utcnow(), **payload.model_dump(exclude={"recorded_at"}))
    db.add(point)

    recent = db.scalars(select(JourneyPoint).where(JourneyPoint.journey_id == journey.id).order_by(JourneyPoint.recorded_at.desc()).limit(5)).all()
    previous = [(p.latitude, p.longitude, p.recorded_at) for p in reversed(recent)]
    score, _ = calculate_risk(
        latitude=payload.latitude,
        longitude=payload.longitude,
        eta=journey.eta,
        battery_level=payload.battery_level,
        previous_points=previous,
    )
    journey.risk_score = score
    db.commit()
    db.refresh(point)
    return point


@router.get("/{journey_id}/points", response_model=list[JourneyPointOut])
def list_points(journey_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    journey = db.scalar(select(Journey).where(Journey.id == journey_id, Journey.owner_id == current_user.id))
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return list(db.scalars(select(JourneyPoint).where(JourneyPoint.journey_id == journey.id).order_by(JourneyPoint.recorded_at.asc()).limit(1000)).all())


@router.post("/{journey_id}/complete", response_model=JourneyOut)
def complete_journey(journey_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    journey = db.scalar(select(Journey).where(Journey.id == journey_id, Journey.owner_id == current_user.id))
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    journey.status = "completed"
    journey.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(journey)
    return journey_out(journey)
