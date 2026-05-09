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
