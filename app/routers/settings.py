from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.supabase import supabase
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/settings", tags=["settings"])

class AlertSettingsUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None
    alert_email: Optional[EmailStr] = None

@router.get("/alerts")
def get_alert_settings(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("profiles")\
        .select("telegram_chat_id, alert_email")\
        .eq("id", user_id)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return result.data[0]

@router.put("/alerts")
def update_alert_settings(
    settings_in: AlertSettingsUpdate, 
    user_id: str = Depends(get_current_user_id)
):
    update_data = {}
    if settings_in.telegram_chat_id is not None:
        update_data["telegram_chat_id"] = settings_in.telegram_chat_id
    if settings_in.alert_email is not None:
        update_data["alert_email"] = str(settings_in.alert_email) if settings_in.alert_email else None
    
    result = supabase.table("profiles")\
        .update(update_data)\
        .eq("id", user_id)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    return {"message": "Settings updated"}
