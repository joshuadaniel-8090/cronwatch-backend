import httpx
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from difflib import get_close_matches

from app.core.config import settings
from app.core.supabase import supabase

router = APIRouter(prefix="/telegram", tags=["telegram"])

# --- HELPERS ---

def escape_md(text: Any) -> str:
    """Escape characters for Telegram MarkdownV2."""
    if text is None:
        return ""
    s = str(text)
    # Characters that must be escaped in MarkdownV2
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    reserved_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(reserved_chars)}])", r"\\\1", s)

def format_response(content: str) -> str:
    """Add standard header and divider to all bot responses."""
    header = "🟣 *Cronwatch*\n"
    divider = "───────────────────\n\n"
    return header + divider + content

async def send_telegram_message(chat_id: int, text: str):
    """Send a MarkdownV2 message to Telegram."""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2"
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                print(f"Telegram API Error: {res.text}")
        except Exception as e:
            print(f"Error sending Telegram message: {str(e)}")

def get_fuzzy_match(query: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fuzzy match item names."""
    if not query:
        return []
    query = query.lower()
    exact = [i for i in items if i["name"].lower() == query]
    if exact:
        return exact
    
    partial = [i for i in items if query in i["name"].lower()]
    return partial

# --- COMMAND HANDLERS ---

async def handle_start(chat_id: int, profile: Optional[Dict]):
    if profile:
        email = escape_md(profile.get("email", "unknown"))
        content = f"👋 *Welcome back\\!*\n\nYour account is linked to:\n📧 `{email}`\n\nUse the menu below or type `/help` for commands\\."
    else:
        content = (
            "👋 *Welcome to Cronwatch\\!*\n\n"
            "To get started, you need to link your account:\n\n"
            "1\\. Copy your Chat ID: `{chat_id}`\n"
            "2\\. Go to *Settings* on the Cronwatch Dashboard\n"
            "3\\. Paste the ID into the *Telegram Chat ID* field\n\n"
            "Once linked, you'll receive instant alerts here\\."
        ).format(chat_id=chat_id)
    
    await send_telegram_message(chat_id, format_response(content))

async def handle_status(chat_id: int, user_id: str):
    # Fetch monitors
    monitors_res = supabase.table("monitors").select("*").eq("user_id", user_id).execute()
    url_monitors_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).execute()
    
    monitors = monitors_res.data or []
    url_monitors = url_monitors_res.data or []
    
    all_monitors = monitors + url_monitors
    if not all_monitors:
        await send_telegram_message(chat_id, format_response("📭 *No monitors found\\.*\nStart by adding one on the dashboard\\."))
        return

    total = len(all_monitors)
    healthy_count = len([m for m in all_monitors if m.get("status") in ("healthy", "up", "waiting") and m.get("is_active", True)])
    score = int((healthy_count / total) * 100) if total > 0 else 100
    
    score_emoji = "🟢" if score >= 90 else "🟡" if score >= 70 else "🔴"
    
    content = f"📊 *System Health: {score_emoji} {score}%*\n\n"
    
    # Heartbeat Group
    h_active = [m for m in monitors if m.get("is_active")]
    h_healthy = len([m for m in h_active if m.get("status") in ("healthy", "waiting")])
    h_failing = len([m for m in h_active if m.get("status") == "failing"])
    h_paused = len([m for m in monitors if not m.get("is_active")])
    
    content += "💓 *Heartbeat Monitors*\n"
    content += f"✅ `{h_healthy}`  ❌ `{h_failing}`  ⏸️ `{h_paused}`\n\n"
    
    # Uptime Group
    u_active = [m for m in url_monitors if m.get("is_active")]
    u_up = len([m for m in u_active if m.get("status") == "up"])
    u_down = len([m for m in u_active if m.get("status") == "down"])
    u_paused = len([m for m in url_monitors if not m.get("is_active")])
    
    content += "🌐 *Uptime Monitors*\n"
    content += f"✅ `{u_up}`  ❌ `{u_down}`  ⏸️ `{u_paused}`\n"
    
    await send_telegram_message(chat_id, format_response(content))

async def handle_list(chat_id: int, user_id: str, page_arg: str):
    page = 1
    try:
        if page_arg:
            page = int(page_arg)
    except:
        pass
    
    limit = 10
    offset = (page - 1) * limit
    
    # Combine and paginate
    monitors_res = supabase.table("monitors").select("*").eq("user_id", user_id).order("name").execute()
    url_monitors_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).order("name").execute()
    
    all_items = []
    for m in (monitors_res.data or []):
        all_items.append({"name": m["name"], "status": m["status"], "active": m["is_active"], "type": "heartbeat", "time": m["last_ping_at"], "interval": m["interval_seconds"]})
    for m in (url_monitors_res.data or []):
        all_items.append({"name": m["name"], "status": m["status"], "active": m["is_active"], "type": "uptime", "time": m["last_checked_at"], "interval": m["check_interval_seconds"]})
    
    all_items.sort(key=lambda x: x["name"].lower())
    
    total = len(all_items)
    items = all_items[offset : offset + limit]
    
    if not items:
        await send_telegram_message(chat_id, format_response("📭 *No monitors to show for this page\\.*"))
        return
        
    content = f"📋 *Monitors \\(Page {page}\\)*\n\n"
    
    # Group in content
    heartbeat = [i for i in items if i["type"] == "heartbeat"]
    uptime = [i for i in items if i["type"] == "uptime"]
    
    if heartbeat:
        content += "💓 *Heartbeat*\n"
        for i in heartbeat:
            emoji = "✅" if i["active"] and i["status"] in ("healthy", "waiting") else "❌" if i["active"] else "⏸️"
            interval = f"{i['interval'] // 60}m" if i["interval"] >= 60 else f"{i['interval']}s"
            content += f"{emoji} `{escape_md(i['name'])}` \\({interval}\\)\n"
        content += "\n"
        
    if uptime:
        content += "🌐 *Uptime*\n"
        for i in uptime:
            emoji = "✅" if i["active"] and i["status"] == "up" else "❌" if i["active"] else "⏸️"
            interval = f"{i['interval'] // 60}m" if i["interval"] >= 60 else f"{i['interval']}s"
            content += f"{emoji} `{escape_md(i['name'])}` \\({interval}\\)\n"
            
    if total > offset + limit:
        content += f"\n👉 Use `/list {page + 1}` for more"
        
    await send_telegram_message(chat_id, format_response(content))

async def handle_pause_resume(chat_id: int, user_id: str, query: str, action: str):
    if not query:
        usage = f"/pause `<name>`" if action == "pause" else f"/resume `<name>`"
        await send_telegram_message(chat_id, format_response(f"⚠️ *Missing monitor name*\nUsage: {usage}"))
        return
        
    # Search both tables
    m_res = supabase.table("monitors").select("*").eq("user_id", user_id).execute()
    u_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).execute()
    
    all_items = (m_res.data or []) + (u_res.data or [])
    matches = get_fuzzy_match(query, all_items)
    
    if not matches:
        await send_telegram_message(chat_id, format_response(f"❌ *No monitor found matching* `{escape_md(query)}`"))
        return
        
    if len(matches) > 1:
        match_list = "\n".join([f"• `{escape_md(m['name'])}`" for m in matches[:5]])
        await send_telegram_message(chat_id, format_response(f"🤔 *Multiple matches found:*\n{match_list}\n\nPlease be more specific\\."))
        return
        
    m = matches[0]
    table = "monitors" if "interval_seconds" in m else "url_monitors"
    is_active = action == "resume"
    
    supabase.table(table).update({"is_active": is_active}).eq("id", m["id"]).execute()
    
    emoji = "▶️" if is_active else "⏸️"
    status_text = "resumed" if is_active else "paused"
    content = f"{emoji} *Monitor {status_text.capitalize()}*\n\n"
    content += f"Name: `{escape_md(m['name'])}`\n"
    content += f"ID: `{m['id'][:8]}\\.\\.\\.`"
    
    await send_telegram_message(chat_id, format_response(content))

async def handle_watch(chat_id: int, user_id: str):
    m_res = supabase.table("monitors").select("*").eq("user_id", user_id).eq("is_active", True).eq("status", "failing").execute()
    u_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).eq("is_active", True).eq("status", "down").execute()
    
    failing = (m_res.data or []) + (u_res.data or [])
    
    if not failing:
        await send_telegram_message(chat_id, format_response("✅ *All systems operational\\.*\nNo failing monitors detected\\."))
        return
        
    content = "⚠️ *Failing Monitors*\n\n"
    for m in failing:
        last_time = m.get("last_ping_at") or m.get("last_checked_at")
        since = ""
        if last_time:
            dt = datetime.fromisoformat(last_time.replace("Z", "+00:00"))
            diff = datetime.now(timezone.utc) - dt
            hours, remainder = divmod(int(diff.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            since = f" \\({hours}h {minutes}m ago\\)"
            
        content += f"❌ `{escape_md(m['name'])}`{since}\n"
        
    await send_telegram_message(chat_id, format_response(content))

async def handle_monitor_detail(chat_id: int, user_id: str, query: str):
    if not query:
        await send_telegram_message(chat_id, format_response("⚠️ *Usage:* `/monitor <name>`"))
        return
        
    m_res = supabase.table("monitors").select("*").eq("user_id", user_id).execute()
    u_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).execute()
    
    all_items = (m_res.data or []) + (u_res.data or [])
    matches = get_fuzzy_match(query, all_items)
    
    if not matches:
        await send_telegram_message(chat_id, format_response(f"❌ *No monitor found matching* `{escape_md(query)}`"))
        return
        
    if len(matches) > 1:
        match_list = "\n".join([f"• `{escape_md(m['name'])}`" for m in matches[:5]])
        await send_telegram_message(chat_id, format_response(f"🤔 *Multiple matches found:*\n{match_list}\n\nPlease be more specific\\."))
        return
        
    m = matches[0]
    is_url = "url" in m
    
    status_emoji = "✅" if m["status"] in ("healthy", "up", "waiting") else "❌"
    
    content = f"{status_emoji} *Monitor Details*\n\n"
    content += f"Name: `{escape_md(m['name'])}`\n"
    content += f"Status: `{m['status'].upper()}`\n"
    
    if is_url:
        content += f"URL: `{escape_md(m['url'])}`\n"
        content += f"Interval: `{m['check_interval_seconds']}s`\n"
        content += f"Last Resp: `{m.get('last_response_time_ms', '0')}ms`\n"
    else:
        content += f"Type: `Heartbeat`\n"
        content += f"Interval: `{m['interval_seconds']}s`\n"
        content += f"Grace: `{m['grace_seconds']}s`\n"
        
    last_check = m.get("last_ping_at") or m.get("last_checked_at")
    content += f"Last Seen: `{escape_md(timeAgo(last_check)) if last_check else 'Never'}`\n"
    
    await send_telegram_message(chat_id, format_response(content))

def timeAgo(iso_str: str) -> str:
    if not iso_str: return "Never"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        diff = datetime.now(timezone.utc) - dt
        if diff.total_seconds() < 60: return "just now"
        if diff.total_seconds() < 3600: return f"{int(diff.total_seconds() // 60)}m ago"
        if diff.total_seconds() < 86400: return f"{int(diff.total_seconds() // 3600)}h ago"
        return f"{int(diff.days)}d ago"
    except:
        return iso_str

async def handle_alerts(chat_id: int, user_id: str):
    # This is slightly complex as alerts are in two different tables possibly or we need to join
    # Let's assume we want last 5 unresolved across all monitors
    alerts_res = supabase.table("alerts").select("*, monitors(name)").eq("is_resolved", False).order("triggered_at", desc=True).limit(5).execute()
    # Note: supabase-py joins might be tricky depending on how they are used. 
    # If standard join fails, we'll just fetch raw and map
    
    alerts = alerts_res.data or []
    if not alerts:
        await send_telegram_message(chat_id, format_response("✅ *No unresolved alerts detected\\.*"))
        return
        
    content = "🚨 *Active Alerts*\n\n"
    for a in alerts:
        m_name = a.get("monitors", {}).get("name", "Unknown")
        dt = datetime.fromisoformat(a["triggered_at"].replace("Z", "+00:00"))
        since = timeAgo(a["triggered_at"])
        content += f"• `{escape_md(m_name)}` triggered `{since}`\n"
        
    await send_telegram_message(chat_id, format_response(content))

async def handle_mute(chat_id: int, user_id: str, args: str, is_unmute: bool = False):
    if not args:
        usage = "/mute `<name>` `<mins>`" if not is_unmute else "/unmute `<name>`"
        await send_telegram_message(chat_id, format_response(f"⚠️ *Usage:* {usage}"))
        return

    parts = args.rsplit(maxsplit=1)
    if is_unmute:
        query = args
        mins = 0
    else:
        if len(parts) < 2:
            await send_telegram_message(chat_id, format_response("⚠️ *Usage:* `/mute <name> <mins>`"))
            return
        query = parts[0]
        try:
            mins = int(parts[1])
        except:
            await send_telegram_message(chat_id, format_response("⚠️ *Invalid minutes provided\\.*"))
            return

    # Find monitor
    m_res = supabase.table("monitors").select("*").eq("user_id", user_id).execute()
    u_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).execute()
    all_items = (m_res.data or []) + (u_res.data or [])
    matches = get_fuzzy_match(query, all_items)
    
    if not matches:
        await send_telegram_message(chat_id, format_response(f"❌ *No monitor found matching* `{escape_md(query)}`"))
        return
    if len(matches) > 1:
        match_list = "\n".join([f"• `{escape_md(m['name'])}`" for m in matches[:5]])
        await send_telegram_message(chat_id, format_response(f"🤔 *Multiple matches found:*\n{match_list}"))
        return
        
    m = matches[0]
    monitor_id = m["id"]
    
    # Get profile to update muted_monitors
    profile_res = supabase.table("profiles").select("muted_monitors").eq("id", user_id).execute()
    muted_monitors = profile_res.data[0].get("muted_monitors") or {}
    
    if is_unmute:
        if monitor_id in muted_monitors:
            del muted_monitors[monitor_id]
        status_text = "unmuted"
    else:
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
        muted_monitors[monitor_id] = expiry
        status_text = f"muted for `{mins}m`"
        
    supabase.table("profiles").update({"muted_monitors": muted_monitors}).eq("id", user_id).execute()
    
    content = f"🔕 *Monitor {status_text.capitalize()}*\n\n"
    content += f"Name: `{escape_md(m['name'])}`"
    
    await send_telegram_message(chat_id, format_response(content))

async def handle_summary(chat_id: int, user_id: str):
    m_res = supabase.table("monitors").select("*").eq("user_id", user_id).execute()
    u_res = supabase.table("url_monitors").select("*").eq("user_id", user_id).execute()
    monitors = (m_res.data or []) + (u_res.data or [])
    
    if not monitors:
        await send_telegram_message(chat_id, format_response("📭 *No data for summary\\.*"))
        return
        
    total = len(monitors)
    active = len([m for m in monitors if m.get("is_active")])
    healthy = len([m for m in monitors if m.get("status") in ("healthy", "up", "waiting") and m.get("is_active")])
    
    uptime = int((healthy / active) * 100) if active > 0 else 100
    
    content = "📈 *Daily Digest Summary*\n\n"
    content += f"Total Monitors: `{total}`\n"
    content += f"Active Health: `{uptime}%`\n"
    content += f"Failing Now: `{active - healthy}`\n\n"
    
    # Find most problematic (just pick one failing if exists)
    failing = [m for m in monitors if m.get("status") in ("failing", "down") and m.get("is_active")]
    if failing:
        content += f"⚠️ *Needs Attention:* `{escape_md(failing[0]['name'])}`"
    else:
        content += "✅ *All systems running smoothly\\.*"
        
    await send_telegram_message(chat_id, format_response(content))

async def handle_help(chat_id: int):
    content = (
        "🤖 *Cronwatch Commands*\n\n"
        "🔍 *Monitoring*\n"
        "/status \\- Overall health overview\n"
        "/list `[page]` \\- Paginated list of monitors\n"
        "/monitor `<name>` \\- Detailed monitor view\n"
        "/watch \\- View failing monitors only\n\n"
        "🚨 *Alerts \\& Control*\n"
        "/alerts \\- Last 5 unresolved alerts\n"
        "/pause `<name>` \\- Stop monitoring\n"
        "/resume `<name>` \\- Start monitoring\n"
        "/mute `<name>` `<mins>` \\- Silence alerts\n"
        "/unmute `<name>` \\- Restore alerts\n\n"
        "👤 *Account*\n"
        "/summary \\- Daily performance digest\n"
        "/chatid \\- Your unique identifier\n"
        "/start \\- Welcome \\& Instructions"
    )
    await send_telegram_message(chat_id, format_response(content))

# --- MAIN WEBHOOK ---

@router.post("/webhook")
async def telegram_webhook(request: Request):
    if settings.TELEGRAM_SECRET_TOKEN:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.TELEGRAM_SECRET_TOKEN:
            raise HTTPException(status_code=403)

    data = await request.json()
    message = data.get("message")
    if not message or "text" not in message:
        return {"status": "ok"}
        
    chat_id = message["chat"]["id"]
    text = message["text"].strip()
    
    parts = text.split(maxsplit=1)
    command = parts[0].lower().split("@")[0] # Strip bot handle if present
    args = parts[1] if len(parts) > 1 else ""

    # Commands that don't need auth
    if command == "/chatid":
        await send_telegram_message(chat_id, format_response(f"🆔 Your Chat ID is:\n`{chat_id}`"))
        return {"status": "ok"}
    
    # Fetch profile
    profile_res = supabase.table("profiles").select("*").eq("telegram_chat_id", str(chat_id)).execute()
    profile = profile_res.data[0] if profile_res.data else None
    
    if command == "/start":
        await handle_start(chat_id, profile)
        return {"status": "ok"}

    if not profile:
        await handle_start(chat_id, None)
        return {"status": "ok"}
        
    user_id = profile["id"]

    try:
        if command == "/status": await handle_status(chat_id, user_id)
        elif command == "/list": await handle_list(chat_id, user_id, args)
        elif command == "/pause": await handle_pause_resume(chat_id, user_id, args, "pause")
        elif command == "/resume": await handle_pause_resume(chat_id, user_id, args, "resume")
        elif command == "/watch": await handle_watch(chat_id, user_id)
        elif command == "/monitor": await handle_monitor_detail(chat_id, user_id, args)
        elif command == "/alerts": await handle_alerts(chat_id, user_id)
        elif command == "/mute": await handle_mute(chat_id, user_id, args)
        elif command == "/unmute": await handle_mute(chat_id, user_id, args, is_unmute=True)
        elif command == "/summary": await handle_summary(chat_id, user_id)
        elif command == "/help": await handle_help(chat_id)
        elif command == "/backend": await handle_backend(chat_id)
        else:
            # Suggest command
            all_cmds = ["/status", "/list", "/monitor", "/watch", "/alerts", "/pause", "/resume", "/mute", "/unmute", "/summary", "/help", "/chatid", "/backend"] 
            # remove /backend from all_cmds for now
            matches = get_close_matches(command, all_cmds, n=1, cutoff=0.6)
            suggestion = f"\n\nDid you mean `{matches[0]}`?" if matches else ""
            await send_telegram_message(chat_id, format_response(f"❓ *Unknown command* `{escape_md(command)}`{suggestion}"))
    except Exception as e:
        print(f"Bot Error: {str(e)}")
        await send_telegram_message(chat_id, format_response("❌ *An internal error occurred\\.*\nOur team has been notified\\."))

    return {"status": "ok"}

async def setup_telegram_webhook():
    if not settings.TELEGRAM_BOT_TOKEN or not settings.API_URL or "localhost" in settings.API_URL:
        return
    webhook_url = f"{settings.API_URL}/telegram/webhook"
    async with httpx.AsyncClient() as client:
        await client.post(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook", json={"url": webhook_url, "secret_token": settings.TELEGRAM_SECRET_TOKEN})

async def handle_backend(chat_id: int):
    api_url = settings.API_URL or "Unknown"

    env = "Production"
    if "localhost" in api_url or "127.0.0.1" in api_url:
        env = "Local Development"
    elif "dev" in api_url:
        env = "Development"
    elif "staging" in api_url:
        env = "Staging"

    content = (
        f"🖥️ *Backend Environment*\n\n"
        f"Environment: `{escape_md(env)}`\n"
        f"API URL:\n`{escape_md(api_url)}`"
    )

    await send_telegram_message(chat_id, format_response(content))