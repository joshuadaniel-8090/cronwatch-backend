from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.ping_checker import check_missed_pings
from app.services.url_checker import check_url_monitors

scheduler = AsyncIOScheduler()

def start_scheduler():
    if not scheduler.running:
        # Check missed pings every minute
        scheduler.add_job(check_missed_pings, 'interval', minutes=1, id="ping_checker")
        
        # Check URL monitors every minute
        scheduler.add_job(check_url_monitors, 'interval', seconds=60, id="url_checker")
        
        scheduler.start()
        print("Scheduler started (Async).")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped.")

