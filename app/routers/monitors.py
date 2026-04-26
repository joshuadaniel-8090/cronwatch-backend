from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user_id, get_or_create_profile
from app.models.profile import Profile
from app.models.monitor import Monitor
from app.models.ping import Ping
from app.schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse
from app.schemas.ping import PingListResponse
from typing import List
import uuid

router = APIRouter(prefix="/monitors", tags=["monitors"])

@router.get("", response_model=List[MonitorResponse])
def list_monitors(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return db.query(Monitor).filter(Monitor.user_id == user_id).order_by(Monitor.created_at.desc()).all()

@router.post("", response_model=MonitorResponse)
def create_monitor(
    monitor_in: MonitorCreate, 
    profile: Profile = Depends(get_or_create_profile), 
    db: Session = Depends(get_db)
):
    if profile.plan == "free":
        count = db.query(Monitor).filter(Monitor.user_id == profile.id).count()
        if count >= 3:
            raise HTTPException(status_code=403, detail="Free plan limit reached (max 3 monitors)")
    
    new_monitor = Monitor(
        user_id=profile.id,
        name=monitor_in.name,
        interval_seconds=monitor_in.interval_seconds,
        grace_seconds=monitor_in.grace_seconds,
        token=str(uuid.uuid4()),
        slug=str(uuid.uuid4())
    )
    db.add(new_monitor)
    db.commit()
    db.refresh(new_monitor)
    return new_monitor

@router.get("/{id}", response_model=MonitorResponse)
def get_monitor(id: uuid.UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == id, Monitor.user_id == user_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor

@router.put("/{id}", response_model=MonitorResponse)
def update_monitor(
    id: uuid.UUID, 
    monitor_in: MonitorUpdate, 
    user_id: str = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    monitor = db.query(Monitor).filter(Monitor.id == id, Monitor.user_id == user_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    monitor.name = monitor_in.name
    monitor.interval_seconds = monitor_in.interval_seconds
    monitor.grace_seconds = monitor_in.grace_seconds
    monitor.is_active = monitor_in.is_active
    
    db.commit()
    db.refresh(monitor)
    return monitor

@router.delete("/{id}")
def delete_monitor(id: uuid.UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == id, Monitor.user_id == user_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    db.delete(monitor)
    db.commit()
    return {"message": "Monitor deleted"}

@router.get("/{id}/pings", response_model=PingListResponse)
def get_monitor_pings(
    id: uuid.UUID, 
    page: int = Query(1, ge=1), 
    limit: int = Query(50, ge=1, le=100), 
    user_id: str = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    monitor = db.query(Monitor).filter(Monitor.id == id, Monitor.user_id == user_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    query = db.query(Ping).filter(Ping.monitor_id == id)
    total = query.count()
    pings = query.order_by(Ping.received_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {"pings": pings, "total": total}
