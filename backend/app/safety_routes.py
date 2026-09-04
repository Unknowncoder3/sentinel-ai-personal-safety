from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .dependencies import get_current_user
from .models import Device, User
from .notification_models import NotificationLog
from .notification_service import build_sos_message, send_email, send_sms, sent_timestamp
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


def dispatch_notifications(event_id: str, owner_id: str, owner_name: str, db_url: str) -> None:
    from .database import SessionLocal

    db = SessionLocal()
    try:
        event = db.scalar(select(SOSEvent).where(SOSEvent.id == event_id, SOSEvent.owner_id == owner_id))
        guardians = db.scalars(select(GuardianContact).where(GuardianContact.owner_id == owner_id)).all()
        if not event:
            return
        body = build_sos_message(owner_name, event.id, event.latitude, event.longitude, event.message)
        subject = f"SENTINEL EMERGENCY ALERT — {owner_name}"
        for guardian in guardians:
            if guardian.email:
                log = NotificationLog(owner_id=owner_id, sos_event_id=event.id, guardian_id=guardian.id, channel="email", destination=guardian.email, status="sending")
                db.add(log)
                db.commit()
                ok, error = send_email(guardian.email, subject, body)
                log.status = "sent" if ok else "failed"
                log.error_message = error
                log.sent_at = sent_timestamp() if ok else None
                db.commit()
            if guardian.phone:
                log = NotificationLog(owner_id=owner_id, sos_event_id=event.id, guardian_id=guardian.id, channel="sms", destination=guardian.phone, status="sending")
                db.add(log)
                db.commit()
                ok, error = send_sms(guardian.phone, body)
                log.status = "sent" if ok else "failed"
                log.error_message = error
                log.sent_at = sent_timestamp() if ok else None
                db.commit()
    finally:
        db.close()


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


@router.get("/notifications")
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(NotificationLog).where(NotificationLog.owner_id == current_user.id).order_by(NotificationLog.created_at.desc()).limit(100)
    ).all()
    return [
        {
            "id": row.id,
            "sos_event_id": row.sos_event_id,
            "guardian_id": row.guardian_id,
            "channel": row.channel,
            "destination": row.destination,
            "status": row.status,
            "error_message": row.error_message,
            "created_at": row.created_at,
            "sent_at": row.sent_at,
        }
        for row in rows
    ]


@router.post("/sos", response_model=SOSOut, status_code=status.HTTP_201_CREATED)
def create_sos(payload: SOSCreate, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.device_id:
        device = db.scalar(select(Device).where(Device.id == payload.device_id, Device.owner_id == current_user.id))
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

    event = SOSEvent(owner_id=current_user.id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    background_tasks.add_task(dispatch_notifications, event.id, current_user.id, current_user.name, settings.database_url)
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
