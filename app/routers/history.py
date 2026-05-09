from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user_id, get_or_create_profile
from app.core.supabase import supabase
from app.schemas.ping import HistoryResponse
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

router = APIRouter(prefix="/history", tags=["history"])

@router.get("", response_model=HistoryResponse)
def get_history(
    monitor_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    profile: dict = Depends(get_or_create_profile)
):
    # 1. Enforce plan-based data retention
    now = datetime.now(timezone.utc)
    max_days = 90 if profile["plan"] == "pro" else 7
    limit_date = (now - timedelta(days=max_days)).isoformat()
    
    if not from_date or from_date < limit_date:
        from_date = limit_date
        
    # 2. Build query
    # We join monitors to filter by user_id and get the monitor name
    # In Postgrest, we can filter on joined table: monitors!inner(user_id)
    query = supabase.table("pings")\
        .select("id, monitor_id, status, received_at, monitors!inner(name, user_id)", count="exact")\
        .eq("monitors.user_id", user_id)\
        .gte("received_at", from_date)
    
    if monitor_id:
        query = query.eq("monitor_id", str(monitor_id))
    if status:
        query = query.eq("status", status)
    if to_date:
        query = query.lte("received_at", to_date)
        
    # 3. Execute with pagination
    result = query\
        .order("received_at", desc=True)\
        .range((page - 1) * limit, page * limit - 1)\
        .execute()
        
    # 4. Transform data to match schema
    events = []
    for p in result.data:
        events.append({
            "id": p["id"],
            "monitor_id": p["monitor_id"],
            "monitor_name": p["monitors"]["name"],
            "status": p["status"],
            "received_at": p["received_at"]
        })
        
    return {"events": events, "total": result.count or 0}
