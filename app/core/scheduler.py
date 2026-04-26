from apscheduler.schedulers.background import BackgroundScheduler
from app.services.ping_checker import check_missed_pings
from app.core.database import SessionLocal

scheduler = BackgroundScheduler()

def start_scheduler():
    def job():
        db = SessionLocal()
        try:
            check_missed_pings(db)
        finally:
            db.close()

    scheduler.add_job(job, "interval", seconds=60, id="ping_checker")
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()
