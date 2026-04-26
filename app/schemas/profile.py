from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional

class ProfileResponse(BaseModel):
    id: UUID
    plan: str
    telegram_chat_id: Optional[str]
    alert_email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AlertSettingsUpdate(BaseModel):
    telegram_chat_id: Optional[str] = None
    alert_email: Optional[EmailStr] = None

class AlertSettingsResponse(BaseModel):
    telegram_chat_id: Optional[str]
    alert_email: Optional[str]
