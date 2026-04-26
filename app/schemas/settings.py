from pydantic import BaseModel, EmailStr
from typing import Optional

class AlertSettingsUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None
    alert_email: Optional[EmailStr] = None

class AlertSettingsResponse(BaseModel):
    telegram_chat_id: Optional[str]
    alert_email: Optional[str]
