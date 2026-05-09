from app.core.supabase import supabase
from app.services.alert_service import send_telegram_alert, send_email_alert
from datetime import datetime, timedelta, timezone
import uuid

import logging

logger = logging.getLogger(__name__)

async def check_missed_pings():
    try:
        # Step 1: Get active monitors only (no join)
        result = supabase.table("monitors")\
            .select("*")\
            .eq("is_active", True)\
            .not_.is_("last_ping_at", "null")\
            .execute()

        monitors = result.data
        now = datetime.now(timezone.utc)

        for monitor in monitors:
            try:
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
                        # Step 2: Get profile separately using user_id
                        profile_result = supabase.table("profiles")\
                            .select("telegram_chat_id, alert_email, muted_monitors")\
                            .eq("id", monitor["user_id"])\
                            .execute()

                        profile = profile_result.data[0] if profile_result.data else {}
                        
                        # Mute Check Logic
                        muted_monitors = profile.get("muted_monitors") or {}
                        is_muted = False
                        if monitor["id"] in muted_monitors:
                            try:
                                expiry_str = muted_monitors[monitor["id"]].replace("Z", "+00:00")
                                expiry = datetime.fromisoformat(expiry_str)
                                if now < expiry:
                                    is_muted = True
                                    logger.info(f"Monitor {monitor['id']} is muted until {expiry}")
                                else:
                                    # Mute expired, cleanup
                                    del muted_monitors[monitor["id"]]
                                    supabase.table("profiles").update({"muted_monitors": muted_monitors}).eq("id", monitor["user_id"]).execute()
                            except Exception as mute_err:
                                logger.error(f"Error checking mute status for {monitor['id']}: {mute_err}")

                        if is_muted:
                            continue

                        # Send Telegram alert
                        if profile.get("telegram_chat_id"):
                            supabase.table("alerts").insert({
                                "id": str(uuid.uuid4()),
                                "monitor_id": monitor["id"],
                                "channel": "telegram",
                                "triggered_at": datetime.now(timezone.utc).isoformat(),
                                "is_resolved": False
                            }).execute()
                            await send_telegram_alert(
                                profile["telegram_chat_id"],
                                monitor["name"],
                                monitor["id"],
                                monitor["interval_seconds"],
                                last_ping
                            )

                        # Send Email alert
                        if profile.get("alert_email"):
                            supabase.table("alerts").insert({
                                "id": str(uuid.uuid4()),
                                "monitor_id": monitor["id"],
                                "channel": "email",
                                "triggered_at": datetime.now(timezone.utc).isoformat(),
                                "is_resolved": False
                            }).execute()
                            await send_email_alert(
                                profile["alert_email"],
                                monitor["name"],
                                monitor["id"],
                                monitor["interval_seconds"],
                                last_ping
                            )
            except Exception as e:
                print(f"Error processing monitor {monitor.get('id')}: {e}")
                
    except Exception as e:
        print(f"ping_checker error: {e}")


