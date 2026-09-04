from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import get_current_user
from .models import Device, User
from .safety_models import GuardianContact, SOSEvent
from .safety_schemas import GuardianCreate, GuardianOut, SOSCreate, SOSOut

router = APIRouter(prefix="/api/v1/safety", tags=["safety"])


def sos_out(event: SOSEvent) -> SOSOut:
    return SOSOut(
        id=event.id, device_id=event.device_id, status=event.status,
        latitude=event.latitude, longitude=event.longitude, message=event.message,
        created_at=event.created_at, acknowledged_at=event.acknowledged_at,
        resolved_at=event.resolved_at,
    )


@router.post("/guardians", response_model=GuardianOut, status_code=status.HTTP_201_CREATED)
def add_guardian(payload: GuardianCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    guardian = GuardianContact(owner_id=current_user.id, **payload.model_dump())
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    return guardian


@router.get("/guardians", response_model=list[GuardianOut])
def list_guardians(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(GuardianContact).where(GuardianContact.owner_id == current_user.id)).all())


@router.post("/sos", response_model=SOSOut, status_code=status.HTTP_201_CREATED)
def create_sos(payload: SOSCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.device_id:
        device = db.scalar(select(Device).where(Device.id == payload.device_id, Device.owner_id == current_user.id))
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

    event = SOSEvent(owner_id=current_user.id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return sos_out(event)


@router.get("/sos", response_model=list[SOSOut])
def list_sos(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    events = db.scalars(
        select(SOSEvent).where(SOSEvent.owner_id == current_user.id).order_by(SOSEvent.created_at.desc()).limit(50)
    ).all()
    return [sos_out(event) for event in events]


@router.post("/sos/{event_id}/acknowledge", response_model=SOSOut)
def acknowledge_sos(event_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = db.scalar(select(SOSEvent).where(SOSEvent.id == event_id, SOSEvent.owner_id == current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="SOS event not found")
    if event.status == "resolved":
        raise HTTPException(status_code=409, detail="SOS event is already resolved")
    event.status = "acknowledged"
    event.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return sos_out(event)


@router.post("/sos/{event_id}/resolve", response_model=SOSOut)
def resolve_sos(event_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = db.scalar(select(SOSEvent).where(SOSEvent.id == event_id, SOSEvent.owner_id == current_user.id))
    if not event:
        raise HTTPException(status_code=404, detail="SOS event not found")
    event.status = "resolved"
    event.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    return sos_out(event)
