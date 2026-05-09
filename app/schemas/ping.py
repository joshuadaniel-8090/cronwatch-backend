from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List

class PingResponse(BaseModel):
    id: UUID
    monitor_id: UUID
    received_at: datetime
    status: str

    class Config:
        from_attributes = True

class PingListResponse(BaseModel):
    pings: List[PingResponse]
    total: int

class PingEventResponse(BaseModel):
    id: UUID
    monitor_id: UUID
    monitor_name: str
    status: str
    received_at: datetime

class HistoryResponse(BaseModel):
    events: List[PingEventResponse]
    total: int
