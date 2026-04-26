from fastapi import APIRouter, Request, HTTPException
import httpx
from app.core.config import settings

router = APIRouter(prefix="/telegram", tags=["telegram"])

@router.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" not in data:
        return {"status": "ok"}
    
    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    
    if text == "/start":
        await send_telegram_message(chat_id, "👋 Welcome to Cronwatch Bot!\n\nTo receive alerts, use /chatid to get your ID, then paste it into your Monitor settings on the dashboard.")
    elif text == "/chatid":
        await send_telegram_message(chat_id, f"Your Chat ID is: `{chat_id}`")
    
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
