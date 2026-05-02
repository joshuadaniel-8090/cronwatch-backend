from fastapi import APIRouter, Request, HTTPException
import httpx
from app.core.config import settings
from app.core.supabase import supabase
from datetime import datetime

router = APIRouter(prefix="/telegram", tags=["telegram"])

@router.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" not in data:
        return {"status": "ok"}
    
    message = data["message"]
    if "chat" not in message or "id" not in message["chat"]:
        return {"status": "ok"}
        
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    
    if not text:
        return {"status": "ok"}

    parts = text.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "/start":
        await send_telegram_message(chat_id, "👋 Welcome to Cronwatch Bot!\n\nTo receive alerts, use /chatid to get your ID, then paste it into your Monitor settings on the dashboard.\n\nUse /help to see all available commands.")
        return {"status": "ok"}
    elif command == "/chatid":
        await send_telegram_message(chat_id, f"Your Chat ID is: `{chat_id}`")
        return {"status": "ok"}
        
    # Check link
    profile_result = supabase.table("profiles").select("*").eq("telegram_chat_id", str(chat_id)).execute()
    if not profile_result.data:
        await send_telegram_message(chat_id, "Your Telegram is not linked to any Cronwatch account. Use /chatid and add it in your settings.")
        return {"status": "ok"}
        
    profile = profile_result.data[0]
    user_id = profile.get("id")
    
    if command == "/status":
        monitors = supabase.table("monitors").select("*").eq("user_id", user_id).execute()
        if not monitors.data:
            await send_telegram_message(chat_id, "📭 You don't have any monitors set up yet.")
            return {"status": "ok"}
            
        healthy = failing = paused = 0
        for m in monitors.data:
            if not m.get("is_active"):
                paused += 1
            elif m.get("status") in ("healthy", "waiting"):
                healthy += 1
            else:
                failing += 1
                
        reply = (
            f"📊 *Monitors Status*\n\n"
            f"✅ Healthy: {healthy}\n"
            f"❌ Failing: {failing}\n"
            f"⏸️ Paused: {paused}"
        )
        await send_telegram_message(chat_id, reply)
        
    elif command == "/list":
        monitors = supabase.table("monitors").select("*").eq("user_id", user_id).order("name").execute()
        if not monitors.data:
            await send_telegram_message(chat_id, "📭 You don't have any monitors set up yet.")
            return {"status": "ok"}
            
        reply = "📋 *Your Monitors*\n\n"
        for m in monitors.data:
            status_emoji = "⏸️" if not m.get("is_active") else ("✅" if m.get("status", "healthy") in ("healthy", "waiting") else "❌")
            last_ping = m.get("last_ping_at")
            if last_ping:
                try:
                    dt = datetime.fromisoformat(last_ping.replace("Z", "+00:00"))
                    ping_text = f"Last ping: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                except:
                    ping_text = f"Last ping: {last_ping}"
            else:
                ping_text = "Never pinged"
            reply += f"{status_emoji} *{m['name']}*\n   _{ping_text}_\n\n"
            
        await send_telegram_message(chat_id, reply)
        
    elif command == "/pause":
        if not args:
            await send_telegram_message(chat_id, "⚠️ Please specify a monitor name. Example: `/pause My Server`")
            return {"status": "ok"}
            
        monitors = supabase.table("monitors").select("*").eq("user_id", user_id).ilike("name", args).execute()
        if not monitors.data:
            await send_telegram_message(chat_id, f"❌ No monitor found matching '{args}'.")
            return {"status": "ok"}
            
        m = monitors.data[0]
        supabase.table("monitors").update({"is_active": False}).eq("id", m["id"]).execute()
        await send_telegram_message(chat_id, f"⏸️ Monitor *{m['name']}* has been paused.")
        
    elif command == "/resume":
        if not args:
            await send_telegram_message(chat_id, "⚠️ Please specify a monitor name. Example: `/resume My Server`")
            return {"status": "ok"}
            
        monitors = supabase.table("monitors").select("*").eq("user_id", user_id).ilike("name", args).execute()
        if not monitors.data:
            await send_telegram_message(chat_id, f"❌ No monitor found matching '{args}'.")
            return {"status": "ok"}
            
        m = monitors.data[0]
        supabase.table("monitors").update({"is_active": True}).eq("id", m["id"]).execute()
        await send_telegram_message(chat_id, f"▶️ Monitor *{m['name']}* has been resumed.")
        
    elif command == "/watch":
        monitors = supabase.table("monitors").select("*").eq("user_id", user_id).eq("is_active", True).order("name").execute()
        if not monitors.data:
            await send_telegram_message(chat_id, "📭 No active monitors found.")
            return {"status": "ok"}
            
        reply = "👀 *Active Monitors*\n\n"
        for m in monitors.data:
            status_emoji = "✅" if m.get("status", "healthy") in ("healthy", "waiting") else "❌"
            reply += f"{status_emoji} *{m['name']}*\n"
            
        await send_telegram_message(chat_id, reply)
        
    elif command == "/help":
        help_text = (
            "🤖 *Cronwatch Bot Commands*\n\n"
            "/start - Get started with Cronwatch\n"
            "/chatid - Get your Telegram Chat ID\n"
            "/status - Show summary status of all monitors\n"
            "/list - List all monitors with last ping time\n"
            "/watch - Show all currently active monitors\n"
            "/pause <name> - Pause a specific monitor\n"
            "/resume <name> - Resume a paused monitor\n"
            "/help - Show this help message"
        )
        await send_telegram_message(chat_id, help_text)
        
    else:
        await send_telegram_message(chat_id, "❓ Unknown command. Use /help to see available commands.")
        
    return {"status": "ok"}

async def send_telegram_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def setup_telegram_webhook():
    if not settings.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set, skipping webhook setup.")
        return
    
    webhook_url = f"{settings.API_URL}/telegram/webhook"
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"url": webhook_url})
            if response.status_code == 200:
                print(f"Telegram webhook set to: {webhook_url}")
            else:
                print(f"Failed to set Telegram webhook: {response.text}")
        except Exception as e:
            print(f"Error setting Telegram webhook: {str(e)}")
