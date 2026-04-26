from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.supabase import supabase
from app.routers.telegram import send_telegram_message
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(prefix="/settings", tags=["settings"])


class AlertSettingsUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None
    alert_email: Optional[EmailStr] = None


class TestAlertRequest(BaseModel):
    type: str  # "telegram" or "email"
    chat_id: Optional[str] = None
    email: Optional[str] = None


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


@router.post("/alerts/test")
async def test_alert(
    body: TestAlertRequest,
    user_id: str = Depends(get_current_user_id)
):
    if body.type == "telegram":
        if not body.chat_id:
            raise HTTPException(status_code=400, detail="chat_id is required")
        try:
            await send_telegram_message(
                int(body.chat_id),
                "✅ *Cronwatch Test Alert*\n\nYour Telegram alerts are working correctly!"
            )
            return {"message": "Test message sent to Telegram"}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid chat_id — must be a number")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send Telegram message: {str(e)}")

    elif body.type == "email":
        raise HTTPException(status_code=501, detail="Email alerts not yet implemented")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported alert type: {body.type}")