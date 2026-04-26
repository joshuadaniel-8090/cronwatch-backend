from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.monitor import Monitor
from app.models.ping import Ping
from app.models.alert import Alert
from datetime import datetime, timezone

router = APIRouter(prefix="/ping", tags=["pings"])

@router.get("/{token}")
def receive_ping(token: str, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.token == token).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    if not monitor.is_active:
        return {"message": "ok"}
    
    now = datetime.now(timezone.utc)
    
    # Create ping record
    new_ping = Ping(monitor_id=monitor.id, received_at=now, status="ok")
    db.add(new_ping)
    
    # Update monitor status
    monitor.last_ping_at = now
    monitor.status = "healthy"
    
    # Resolve any open alerts
    unresolved_alerts = db.query(Alert).filter(
        Alert.monitor_id == monitor.id,
        Alert.is_resolved == False
    ).all()
    
    for alert in unresolved_alerts:
        alert.is_resolved = True
        alert.resolved_at = now
    
    db.commit()
    return {"message": "ok"}
