import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.monitor import Monitor
from app.models.alert import Alert
from app.models.profile import Profile
from app.services.alert_service import send_telegram_alert, send_email_alert
import logging

logger = logging.getLogger(__name__)

def check_missed_pings(db: Session):
    """
    Runs every 60 seconds via APScheduler.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Fetch all active monitors where last_ping_at is not null
    monitors = db.query(Monitor).filter(
        Monitor.is_active == True,
        Monitor.last_ping_at.isnot(None)
    ).all()
    
    for monitor in monitors:
        # 2. For each monitor:
        # a. deadline = last_ping_at + interval_seconds + grace_seconds
        deadline = monitor.last_ping_at + timedelta(seconds=monitor.interval_seconds + monitor.grace_seconds)
        
        # b. if utcnow() > deadline AND monitor.status != "failing":
        if now > deadline and monitor.status != "failing":
            monitor.status = "failing"
            
            # check if unresolved alert already exists
            unresolved_alert = db.query(Alert).filter(
                Alert.monitor_id == monitor.id,
                Alert.is_resolved == False
            ).first()
            
            if not unresolved_alert:
                # fetch profile for monitor.user_id
                profile = db.query(Profile).filter(Profile.id == monitor.user_id).first()
                
                if profile:
                    if profile.telegram_chat_id:
                        alert_tg = Alert(monitor_id=monitor.id, channel="telegram")
                        db.add(alert_tg)
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(send_telegram_alert(
                                profile.telegram_chat_id, 
                                monitor.name, 
                                str(monitor.id),
                                monitor.interval_seconds, 
                                monitor.last_ping_at
                            ))
                            loop.close()
                        except Exception as e:
                            logger.error(f"Error sending Telegram alert: {e}")

                    if profile.alert_email:
                        alert_email = Alert(monitor_id=monitor.id, channel="email")
                        db.add(alert_email)
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(send_email_alert(
                                profile.alert_email, 
                                monitor.name, 
                                str(monitor.id),
                                monitor.interval_seconds, 
                                monitor.last_ping_at
                            ))
                            loop.close()
                        except Exception as e:
                            logger.error(f"Error sending email alert: {e}")

    db.commit()
    logger.info(f"Ping check completed at {now}")
