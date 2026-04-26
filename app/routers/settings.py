from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_or_create_profile
from app.models.profile import Profile
from app.schemas.profile import AlertSettingsUpdate, AlertSettingsResponse
from app.services.alert_service import send_test_telegram, send_test_email

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/alerts", response_model=AlertSettingsResponse)
def get_alert_settings(profile: Profile = Depends(get_or_create_profile)):
    return {
        "telegram_chat_id": profile.telegram_chat_id,
        "alert_email": profile.alert_email
    }

@router.put("/alerts")
def update_alert_settings(
    settings_in: AlertSettingsUpdate, 
    profile: Profile = Depends(get_or_create_profile), 
    db: Session = Depends(get_db)
):
    if settings_in.telegram_chat_id is not None:
        profile.telegram_chat_id = settings_in.telegram_chat_id
    if settings_in.alert_email is not None:
        profile.alert_email = settings_in.alert_email
    
    db.commit()
    return {"message": "saved"}

@router.post("/test-alert")
async def test_alert(profile: Profile = Depends(get_or_create_profile)):
    if not profile.telegram_chat_id and not profile.alert_email:
        raise HTTPException(status_code=400, detail="No alert channels configured")
    
    if profile.telegram_chat_id:
        try:
            await send_test_telegram(profile.telegram_chat_id)
        except Exception:
            pass
            
    if profile.alert_email:
        try:
            await send_test_email(profile.alert_email)
        except Exception:
            pass
            
    return {"message": "test alert sent"}
