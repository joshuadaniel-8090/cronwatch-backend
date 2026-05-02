from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.auth import get_current_user_id, get_or_create_profile
from app.core.supabase import supabase
from app.schemas.monitor import MonitorCreate, MonitorUpdate, MonitorResponse
from app.schemas.ping import PingListResponse
from typing import List
import uuid

router = APIRouter(prefix="/monitors", tags=["monitors"])

@router.get("", response_model=List[MonitorResponse])
def list_monitors(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("monitors")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()
    return result.data

@router.post("", response_model=MonitorResponse)
def create_monitor(
    monitor_in: MonitorCreate, 
    profile: dict = Depends(get_or_create_profile)
):
    # Check monitor count for free plan
    count_result = supabase.table("monitors")\
        .select("id", count="exact")\
        .eq("user_id", profile["id"])\
        .execute()
    count = count_result.count or 0

    if profile["plan"] == "free" and count >= 15:
        raise HTTPException(status_code=403, detail="Free plan limit reached (max 3 monitors)")
    
    new_monitor = {
        "id": str(uuid.uuid4()),
        "user_id": profile["id"],
        "name": monitor_in.name,
        "interval_seconds": monitor_in.interval_seconds,
        "grace_seconds": monitor_in.grace_seconds,
        "token": str(uuid.uuid4()),
        "slug": str(uuid.uuid4()),
        "status": "waiting",
        "is_active": True
    }
    
    result = supabase.table("monitors").insert(new_monitor).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create monitor")
        
    return result.data[0]

@router.get("/{id}", response_model=MonitorResponse)
def get_monitor(id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    result = supabase.table("monitors")\
        .select("*")\
        .eq("id", str(id))\
        .eq("user_id", user_id)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return result.data[0]

@router.put("/{id}", response_model=MonitorResponse)
def update_monitor(
    id: uuid.UUID, 
    monitor_in: MonitorUpdate, 
    user_id: str = Depends(get_current_user_id)
):
    update_data = {
        "name": monitor_in.name,
        "interval_seconds": monitor_in.interval_seconds,
        "grace_seconds": monitor_in.grace_seconds,
        "is_active": monitor_in.is_active
    }
    
    result = supabase.table("monitors")\
        .update(update_data)\
        .eq("id", str(id))\
        .eq("user_id", user_id)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return result.data[0]

@router.delete("/{id}")
def delete_monitor(id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    result = supabase.table("monitors")\
        .delete()\
        .eq("id", str(id))\
        .eq("user_id", user_id)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
        
    return {"message": "Monitor deleted"}

@router.get("/{id}/pings", response_model=PingListResponse)
def get_monitor_pings(
    id: uuid.UUID, 
    page: int = Query(1, ge=1), 
    limit: int = Query(50, ge=1, le=100), 
    user_id: str = Depends(get_current_user_id)
):
    # Verify ownership
    monitor_result = supabase.table("monitors")\
        .select("id")\
        .eq("id", str(id))\
        .eq("user_id", user_id)\
        .execute()
        
    if not monitor_result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Get pings count
    count_result = supabase.table("pings")\
        .select("id", count="exact")\
        .eq("monitor_id", str(id))\
        .execute()
    total = count_result.count or 0
    
    # Get pings data
    pings_result = supabase.table("pings")\
        .select("*")\
        .eq("monitor_id", str(id))\
        .order("received_at", desc=True)\
        .range((page - 1) * limit, page * limit - 1)\
        .execute()
    
    return {"pings": pings_result.data, "total": total}
