from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.ping_checker import check_missed_pings

scheduler = AsyncIOScheduler()

def start_scheduler():
    if not scheduler.running:
        # Run every 60 seconds
        scheduler.add_job(check_missed_pings, 'interval', minutes=1)
        scheduler.start()
        print("Scheduler started (Async).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped.")

