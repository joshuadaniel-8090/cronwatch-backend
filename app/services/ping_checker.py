from app.core.supabase import supabase
from app.services.alert_service import send_telegram_alert, send_email_alert
from datetime import datetime, timedelta, timezone

def check_missed_pings():
    # Get all active monitors that have been pinged at least once
    # We join with profiles to get alert settings in one go
    result = supabase.table("monitors")\
        .select("*, profiles(telegram_chat_id, alert_email)")\
        .eq("is_active", True)\
        .not_.is_("last_ping_at", "null")\
        .execute()

    monitors = result.data
    now = datetime.now(timezone.utc)

    for monitor in monitors:
        # Parse timestamp from Supabase (ISO format)
        last_ping_str = monitor["last_ping_at"].replace("Z", "+00:00")
        last_ping = datetime.fromisoformat(last_ping_str)
        
        # Calculate deadline
        deadline = last_ping + timedelta(seconds=monitor["interval_seconds"] + (monitor["grace_seconds"] or 60))

        if now > deadline and monitor["status"] != "failing":
            print(f"Monitor {monitor['name']} ({monitor['id']}) is failing!")
            
            # Mark as failing
            supabase.table("monitors").update({
                "status": "failing"
            }).eq("id", monitor["id"]).execute()

            # Check for existing unresolved alert
            existing = supabase.table("alerts")\
                .select("id")\
                .eq("monitor_id", monitor["id"])\
                .eq("is_resolved", False)\
                .execute()

            if not existing.data:
                profile = monitor.get("profiles")
                if not profile:
                    # Fallback if join didn't work as expected
                    profile_res = supabase.table("profiles")\
                        .select("telegram_chat_id, alert_email")\
                        .eq("id", monitor["user_id"])\
                        .execute()
                    profile = profile_res.data[0] if profile_res.data else {}

                # Send Telegram alert
                if profile.get("telegram_chat_id"):
                    supabase.table("alerts").insert({
                        "monitor_id": monitor["id"],
                        "channel": "telegram"
                    }).execute()
                    send_telegram_alert(
                        profile["telegram_chat_id"],
                        monitor["name"],
                        monitor["id"],
                        monitor["interval_seconds"],
                        monitor["last_ping_at"]
                    )

                # Send Email alert
                if profile.get("alert_email"):
                    supabase.table("alerts").insert({
                        "monitor_id": monitor["id"],
                        "channel": "email"
                    }).execute()
                    send_email_alert(
                        profile["alert_email"],
                        monitor["name"],
                        monitor["id"],
                        monitor["interval_seconds"],
                        monitor["last_ping_at"]
                    )
