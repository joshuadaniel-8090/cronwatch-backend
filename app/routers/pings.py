from fastapi import APIRouter, HTTPException
from app.core.supabase import supabase
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/ping", tags=["pings"])

@router.get("/{token}")
def receive_ping(token: str):
    # Find monitor by token
    result = supabase.table("monitors")\
        .select("*")\
        .eq("token", token)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    monitor = result.data[0]
    
    if not monitor["is_active"]:
        return {"message": "ok"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Record ping
    supabase.table("pings").insert({
        "id": str(uuid.uuid4()),
        "monitor_id": monitor["id"],
        "status": "ok",
        "received_at": now
    }).execute()
    
    # Update monitor status
    supabase.table("monitors").update({
        "last_ping_at": now,
        "status": "healthy"
    }).eq("id", monitor["id"]).execute()
    
    # Resolve any open alerts
    supabase.table("alerts").update({
        "is_resolved": True,
        "resolved_at": now
    }).eq("monitor_id", monitor["id"])\
      .eq("is_resolved", False)\
      .execute()
    
    return {"message": "ok"}
