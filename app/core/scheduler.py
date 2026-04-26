from apscheduler.schedulers.background import BackgroundScheduler
from app.services.ping_checker import check_missed_pings

scheduler = BackgroundScheduler()

def start_scheduler():
    if not scheduler.running:
        # Run every 60 seconds
        scheduler.add_job(check_missed_pings, 'interval', minutes=1)
        scheduler.start()
        print("Scheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("Scheduler stopped.")
