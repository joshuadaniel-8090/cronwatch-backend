from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class MonitorBase(BaseModel):
    name: str
    interval_seconds: int
    grace_seconds: int = 60

class MonitorCreate(MonitorBase):
    pass

class MonitorUpdate(MonitorBase):
    is_active: bool

class MonitorResponse(MonitorBase):
    id: UUID
    user_id: UUID
    token: str
    slug: str
    is_active: bool
    last_ping_at: Optional[datetime]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
