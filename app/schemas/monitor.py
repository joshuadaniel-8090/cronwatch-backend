from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional

class MonitorBase(BaseModel):
    name: str
    interval_seconds: int
    grace_seconds: int = 60

class MonitorCreate(MonitorBase):
    pass

class MonitorUpdate(MonitorBase):
    is_active: bool = True

class MonitorResponse(MonitorBase):
    id: UUID
    user_id: UUID
    token: str
    slug: str
    is_active: bool = True          # default handles None from DB
    last_ping_at: Optional[datetime] = None
    status: str = "active"
    created_at: datetime

    @field_validator("is_active", mode="before")
    @classmethod
    def coerce_is_active(cls, v):
        if v is None:
            return True
        return bool(v)

    class Config:
        from_attributes = True

class MonitorStatsResponse(BaseModel):
    total_pings: int
    successful_pings: int
    failed_pings: int
    uptime_percentage: float
    last_ping_at: Optional[datetime]
    current_status: str