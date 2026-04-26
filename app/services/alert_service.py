import httpx
import resend
from datetime import datetime
from typing import Optional
from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY

def format_interval(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    elif seconds < 86400:
        return f"{seconds // 3600} hours"
    else:
        return f"{seconds // 86400} days"

async def send_telegram_alert(
    chat_id: str, 
    monitor_name: str, 
    monitor_id: str,
    interval_seconds: int, 
    last_ping_at: Optional[datetime]
):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    last_ping_str = last_ping_at.strftime("%Y-%m-%d %H:%M:%S UTC") if last_ping_at else "Never"
    interval_str = format_interval(interval_seconds)
    
    message = (
        "🚨 Cronwatch Alert\n\n"
        f"Monitor: {monitor_name}\n"
        "Status: MISSED PING\n"
        f"Expected every: {interval_str}\n"
        f"Last ping: {last_ping_str}\n\n"
        f"View: {settings.APP_URL}/monitors/{monitor_id}"
    )
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": message})

async def send_email_alert(
    to_email: str, 
    monitor_name: str, 
    monitor_id: str,
    interval_seconds: int, 
    last_ping_at: Optional[datetime]
):
    last_ping_str = last_ping_at.strftime("%Y-%m-%d %H:%M:%S UTC") if last_ping_at else "Never"
    interval_str = format_interval(interval_seconds)
    
    html_content = f"""
    <h2>⚠️ {monitor_name} missed its scheduled ping</h2>
    <p><strong>Status:</strong> MISSED PING</p>
    <p><strong>Expected every:</strong> {interval_str}</p>
    <p><strong>Last ping:</strong> {last_ping_str}</p>
    <p><a href="{settings.APP_URL}/monitors/{monitor_id}">View Dashboard</a></p>
    """
    
    params = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": f"⚠️ {monitor_name} missed its scheduled ping",
        "html": html_content,
    }
    
    resend.Emails.send(params)

async def send_test_telegram(chat_id: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    message = "✅ Cronwatch test alert — your Telegram alerts are working!"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": message})

async def send_test_email(to_email: str):
    params = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": "✅ Cronwatch test alert",
        "html": "<p>Cronwatch test alert — your email alerts are working!</p>",
    }
    resend.Emails.send(params)
