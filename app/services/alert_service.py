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

async def send_recovery_telegram_alert(
    chat_id: str,
    monitor_name: str,
    pinged_at_str: str
):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    message = f"✅ *{monitor_name}* is back to normal! Ping received at {pinged_at_str}."
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

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

async def send_recovery_email_alert(
    to_email: str,
    monitor_name: str,
    pinged_at_str: str
):
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px;">
        <h2 style="color: #10b981;">✅ {monitor_name} is back to normal</h2>
        <p>Your monitor has recovered and is now reporting <strong>HEALTHY</strong> status.</p>
        <p><strong>Ping received at:</strong> {pinged_at_str}</p>
        <p style="margin-top: 20px;">
            <a href="{settings.APP_URL}/monitors" style="background-color: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Dashboard</a>
        </p>
    </div>
    """
    
    params = {
        "from": settings.FROM_EMAIL,
        "to": [to_email],
        "subject": f"✅ {monitor_name} is back to normal",
        "html": html_content,
    }
    
    resend.Emails.send(params)

async def send_recovery_alerts(profile: dict, monitor_name: str, pinged_at: datetime):
    pinged_at_str = pinged_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    if profile.get("telegram_chat_id"):
        await send_recovery_telegram_alert(profile["telegram_chat_id"], monitor_name, pinged_at_str)
        
    if profile.get("alert_email"):
        await send_recovery_email_alert(profile["alert_email"], monitor_name, pinged_at_str)

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

async def send_url_down_alert(
    profile: dict,
    name: str,
    url: str,
    error_message: Optional[str],
    checked_at: datetime,
    monitor_id: str
):
    checked_at_str = checked_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Telegram
    if profile.get("telegram_chat_id"):
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        message = (
            "🔴 *Cronwatch URL Alert*\n\n"
            f"Monitor: {name}\n"
            f"URL: {url}\n"
            "Status: DOWN\n"
            f"Error: {error_message or 'Connection failed'}\n"
            f"Checked at: {checked_at_str}\n\n"
            f"View: {settings.APP_URL}/url-monitors/{monitor_id}"
        )
        async with httpx.AsyncClient() as client:
            await client.post(telegram_url, json={"chat_id": profile["telegram_chat_id"], "text": message, "parse_mode": "Markdown"})

    # Email
    if profile.get("alert_email"):
        html_content = f"""
        <h2 style="color: #ef4444;">🔴 {name} is DOWN</h2>
        <p><strong>URL:</strong> {url}</p>
        <p><strong>Error:</strong> {error_message or 'Connection failed'}</p>
        <p><strong>Checked at:</strong> {checked_at_str}</p>
        <p><a href="{settings.APP_URL}/url-monitors/{monitor_id}">View Dashboard</a></p>
        """
        params = {
            "from": settings.FROM_EMAIL,
            "to": [profile["alert_email"]],
            "subject": f"🔴 {name} is DOWN — {url}",
            "html": html_content,
        }
        resend.Emails.send(params)

async def send_url_recovery_alert(
    profile: dict,
    name: str,
    url: str,
    response_time_ms: int,
    monitor_id: str
):
    # Telegram
    if profile.get("telegram_chat_id"):
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        message = (
            "✅ *Cronwatch Recovery*\n\n"
            f"Monitor: {name}\n"
            f"URL: {url}\n"
            "Status: BACK UP\n"
            f"Response time: {response_time_ms}ms\n\n"
            f"View: {settings.APP_URL}/url-monitors/{monitor_id}"
        )
        async with httpx.AsyncClient() as client:
            await client.post(telegram_url, json={"chat_id": profile["telegram_chat_id"], "text": message, "parse_mode": "Markdown"})

    # Email
    if profile.get("alert_email"):
        html_content = f"""
        <h2 style="color: #10b981;">✅ {name} is back UP</h2>
        <p><strong>URL:</strong> {url}</p>
        <p><strong>Response time:</strong> {response_time_ms}ms</p>
        <p><a href="{settings.APP_URL}/url-monitors/{monitor_id}">View Dashboard</a></p>
        """
        params = {
            "from": settings.FROM_EMAIL,
            "to": [profile["alert_email"]],
            "subject": f"✅ {name} is back UP",
            "html": html_content,
        }
        resend.Emails.send(params)

