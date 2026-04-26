from fastapi import APIRouter, HTTPException
from app.core.supabase import supabase
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/status", tags=["status"])

@router.get("/{slug}")
def get_public_status(slug: str):
    # Find monitor by slug
    result = supabase.table("monitors")\
        .select("*")\
        .eq("slug", slug)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    monitor = result.data[0]
    
    # Get last 30 days of pings for the uptime chart
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    pings_result = supabase.table("pings")\
        .select("received_at, status")\
        .eq("monitor_id", monitor["id"])\
        .gte("received_at", thirty_days_ago)\
        .order("received_at", desc=True)\
        .execute()
    
    return {
        "monitor": {
            "name": monitor["name"],
            "status": monitor["status"],
            "last_ping_at": monitor["last_ping_at"],
            "interval_seconds": monitor["interval_seconds"]
        },
        "pings": pings_result.data
    }
