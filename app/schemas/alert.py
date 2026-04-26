from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class AlertResponse(BaseModel):
    id: UUID
    monitor_id: UUID
    triggered_at: datetime
    channel: str
    is_resolved: bool
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
