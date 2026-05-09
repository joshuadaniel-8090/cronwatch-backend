from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.auth import get_current_user_id
from app.core.supabase import supabase
from app.schemas.url_monitor import (
    URLMonitorCreate, 
    URLMonitorUpdate, 
    URLMonitorResponse, 
    URLMonitorLogResponse,
    URLTestRequest,
    URLTestResponse
)
from app.services.url_checker import check_single_url
from typing import List
import uuid

router = APIRouter(prefix="/url-monitors", tags=["url-monitors"])

@router.get("", response_model=List[URLMonitorResponse])
def list_url_monitors(user_id: str = Depends(get_current_user_id)):
    result = supabase.table("url_monitors").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data

@router.post("/test", response_model=URLTestResponse)
async def test_url_monitor(body: URLTestRequest, user_id: str = Depends(get_current_user_id)):
    """
    Test a URL without creating a monitor.
    """
    url = str(body.url)
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL format. Must start with http:// or https://")
        
    result = await check_single_url(url)
    return result

@router.post("", response_model=URLMonitorResponse)
def create_url_monitor(body: URLMonitorCreate, user_id: str = Depends(get_current_user_id)):
    # 1. Check plan limits
    profile_res = supabase.table("profiles").select("plan").eq("id", user_id).single().execute()
    profile = profile_res.data
    
    count_res = supabase.table("url_monitors").select("id", count="exact").eq("user_id", user_id).execute()
    count = count_res.count or 0

    if profile["plan"] == "free" and count >= 3:
        raise HTTPException(
            status_code=403,
            detail="Free plan allows max 3 URL monitors. Upgrade to Pro for unlimited."
        )

    # 2. Enforce minimum interval
    if profile["plan"] == "free" and body.check_interval_seconds < 300:
        raise HTTPException(
            status_code=403,
            detail="Free plan minimum check interval is 5 minutes (300s). Upgrade to Pro for 1 minute checks."
        )
    elif body.check_interval_seconds < 60:
        raise HTTPException(
            status_code=403,
            detail="Minimum check interval is 60 seconds."
        )

    # 3. Create
    new_monitor = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": body.name,
        "url": body.url,
        "check_interval_seconds": body.check_interval_seconds,
        "is_active": True,
        "status": "waiting"
    }
    
    res = supabase.table("url_monitors").insert(new_monitor).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create URL monitor")
    
    return res.data[0]

@router.get("/{id}", response_model=URLMonitorResponse)
def get_url_monitor(id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    res = supabase.table("url_monitors").select("*").eq("id", str(id)).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="URL monitor not found")
    return res.data[0]

@router.put("/{id}", response_model=URLMonitorResponse)
def update_url_monitor(id: uuid.UUID, body: URLMonitorUpdate, user_id: str = Depends(get_current_user_id)):
    # Verify ownership
    existing = supabase.table("url_monitors").select("*").eq("id", str(id)).eq("user_id", user_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="URL monitor not found")

    update_data = body.model_dump(exclude_unset=True)
    
    # Plan enforcement on update
    if "check_interval_seconds" in update_data:
        profile_res = supabase.table("profiles").select("plan").eq("id", user_id).single().execute()
        if profile_res.data["plan"] == "free" and update_data["check_interval_seconds"] < 300:
            raise HTTPException(status_code=403, detail="Free plan minimum interval is 5 minutes.")
        elif update_data["check_interval_seconds"] < 60:
            raise HTTPException(status_code=403, detail="Minimum check interval is 60 seconds.")

    res = supabase.table("url_monitors").update(update_data).eq("id", str(id)).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to update URL monitor")
    return res.data[0]

@router.delete("/{id}")
def delete_url_monitor(id: uuid.UUID, user_id: str = Depends(get_current_user_id)):
    res = supabase.table("url_monitors").delete().eq("id", str(id)).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="URL monitor not found")
    return {"message": "Deleted successfully"}

@router.get("/{id}/logs", response_model=List[URLMonitorLogResponse])
def get_url_monitor_logs(
    id: uuid.UUID, 
    page: int = Query(1, ge=1), 
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id)
):
    # Verify ownership
    existing = supabase.table("url_monitors").select("id").eq("id", str(id)).eq("user_id", user_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="URL monitor not found")

    res = supabase.table("url_monitor_logs")\
        .select("*")\
        .eq("url_monitor_id", str(id))\
        .order("checked_at", desc=True)\
        .range((page-1)*limit, page*limit-1)\
        .execute()
    
    return res.data
