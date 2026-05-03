from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional
import uuid

class URLMonitorBase(BaseModel):
    name: str
    url: str
    check_interval_seconds: int = 600

class URLMonitorCreate(URLMonitorBase):
    pass

class URLMonitorUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    check_interval_seconds: Optional[int] = None
    is_active: Optional[bool] = None

class URLMonitorResponse(URLMonitorBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    status: str
    last_checked_at: Optional[datetime] = None
    last_response_time_ms: Optional[int] = None
    last_status_code: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class URLMonitorLogResponse(BaseModel):
    id: uuid.UUID
    url_monitor_id: uuid.UUID
    checked_at: datetime
    status: str
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
