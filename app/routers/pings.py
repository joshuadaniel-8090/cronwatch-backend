from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.core.supabase import supabase
from app.services.alert_service import send_recovery_alerts
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/ping", tags=["pings"])

@router.get("/{token}")
async def receive_ping(token: str, background_tasks: BackgroundTasks):
    # Find monitor by token
    result = supabase.table("monitors")\
        .select("*")\
        .eq("token", token)\
        .execute()
        
    if not result.data:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    monitor = result.data[0]
    
    if not monitor["is_active"]:
        return {
            "status": "received",
            "monitor": monitor["name"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "message": f"Ping received for '{monitor['name']}'. Your job is healthy."
        }
    
    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    
    is_recovery = monitor["status"] == "failing"
    
    # Record ping
    supabase.table("pings").insert({
        "id": str(uuid.uuid4()),
        "monitor_id": monitor["id"],
        "status": "recovery" if is_recovery else "ok",
        "received_at": now
    }).execute()
    
    # Update monitor status
    supabase.table("monitors").update({
        "last_ping_at": now,
        "status": "healthy"
    }).eq("id", monitor["id"]).execute()
    
    # Handle recovery logic
    if is_recovery:
        # Resolve any open alerts in database
        supabase.table("alerts").update({
            "is_resolved": True,
            "resolved_at": now
        }).eq("monitor_id", monitor["id"])\
          .eq("is_resolved", False)\
          .execute()
          
        # Fetch profile for alert destinations
        profile_result = supabase.table("profiles")\
            .select("telegram_chat_id, alert_email")\
            .eq("id", monitor["user_id"])\
            .execute()
            
        if profile_result.data:
            profile = profile_result.data[0]
            # Send recovery alerts in background
            background_tasks.add_task(
                send_recovery_alerts, 
                profile, 
                monitor["name"], 
                now_dt
            )
    else:
        # Still resolve alerts even if not failing (e.g. waiting -> healthy)
        supabase.table("alerts").update({
            "is_resolved": True,
            "resolved_at": now
        }).eq("monitor_id", monitor["id"])\
          .eq("is_resolved", False)\
          .execute()
    
    return {"message": "ok"}

