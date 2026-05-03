import httpx
from datetime import datetime, timezone
import uuid
from app.core.supabase import supabase
from app.services.alert_service import send_url_down_alert, send_url_recovery_alert

async def check_url_monitors():
    """
    Runs every 60 seconds via APScheduler.
    Only checks monitors whose check interval has elapsed.
    """
    try:
        # 1. Get active monitors
        result = supabase.table("url_monitors").select("*").eq("is_active", True).execute()
        monitors = result.data
        if not monitors:
            return

        now = datetime.now(timezone.utc)

        for monitor in monitors:
            try:
                # 2. Check if it's time to check
                last_checked = monitor.get("last_checked_at")
                if last_checked:
                    # Handle both Z and +00:00 formats
                    last_checked_str = last_checked.replace("Z", "+00:00")
                    last_checked_dt = datetime.fromisoformat(last_checked_str)
                    elapsed = (now - last_checked_dt).total_seconds()
                    if elapsed < monitor["check_interval_seconds"]:
                        continue

                # 3. Perform check
                check_result = await check_single_url(monitor["url"])
                
                # 4. Record log
                supabase.table("url_monitor_logs").insert({
                    "id": str(uuid.uuid4()),
                    "url_monitor_id": monitor["id"],
                    "status": check_result["status"],
                    "response_time_ms": check_result["response_time_ms"],
                    "status_code": check_result["status_code"],
                    "error_message": check_result["error_message"],
                    "checked_at": now.isoformat()
                }).execute()

                # 5. Update monitor
                old_status = monitor["status"]
                new_status = check_result["status"]
                
                supabase.table("url_monitors").update({
                    "last_checked_at": now.isoformat(),
                    "last_response_time_ms": check_result["response_time_ms"],
                    "last_status_code": check_result["status_code"],
                    "status": new_status
                }).eq("id", monitor["id"]).execute()

                # 6. Alerts
                if new_status == "down" and old_status != "down":
                    # Check for existing unresolved alert
                    existing = supabase.table("url_monitor_alerts")\
                        .select("id")\
                        .eq("url_monitor_id", monitor["id"])\
                        .eq("is_resolved", False)\
                        .execute()

                    if not existing.data:
                        # Get user profile
                        profile_res = supabase.table("profiles").select("*").eq("id", monitor["user_id"]).execute()
                        if profile_res.data:
                            profile = profile_res.data[0]
                            
                            # Create alert record
                            supabase.table("url_monitor_alerts").insert({
                                "id": str(uuid.uuid4()),
                                "url_monitor_id": monitor["id"],
                                "channel": "both",
                                "triggered_at": now.isoformat(),
                                "is_resolved": False
                            }).execute()

                            await send_url_down_alert(
                                profile,
                                monitor["name"],
                                monitor["url"],
                                check_result["error_message"] or (f"Status Code: {check_result['status_code']}" if check_result['status_code'] else "Failed"),
                                now,
                                monitor["id"]
                            )

                elif new_status == "up" and old_status == "down":
                    # Resolve alerts
                    supabase.table("url_monitor_alerts").update({
                        "is_resolved": True,
                        "resolved_at": now.isoformat()
                    }).eq("url_monitor_id", monitor["id"]).eq("is_resolved", False).execute()

                    # Send recovery alert
                    profile_res = supabase.table("profiles").select("*").eq("id", monitor["user_id"]).execute()
                    if profile_res.data:
                        profile = profile_res.data[0]
                        await send_url_recovery_alert(
                            profile,
                            monitor["name"],
                            monitor["url"],
                            check_result["response_time_ms"] or 0,
                            monitor["id"]
                        )

            except Exception as e:
                print(f"Error checking monitor {monitor.get('id', 'unknown')}: {str(e)}")

    except Exception as e:
        print(f"Fatal error in check_url_monitors: {str(e)}")

async def check_single_url(url: str) -> dict:
    """
    Makes HTTP GET request to url.
    Returns:
    {
      "status": "up" | "down",
      "status_code": int | None,
      "response_time_ms": int | None,
      "error_message": str | None
    }
    """
    start = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url)
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return {
                "status": "up" if response.status_code < 400 else "down",
                "status_code": response.status_code,
                "response_time_ms": int(elapsed),
                "error_message": None
            }
    except Exception as e:
        return {
            "status": "down",
            "status_code": None,
            "response_time_ms": None,
            "error_message": str(e)
        }
