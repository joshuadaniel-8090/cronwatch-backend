from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.scheduler import start_scheduler, stop_scheduler
from app.routers import monitors, pings, settings, status, profile, auth, telegram, url_monitors, history
from app.routers.telegram import setup_telegram_webhook

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    await setup_telegram_webhook()
    yield
    stop_scheduler()

app = FastAPI(title="Cronwatch API", version="1.0.0", lifespan=lifespan)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # temporary for testing
    allow_credentials=False,  # must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(monitors.router)
app.include_router(pings.router)
app.include_router(url_monitors.router)
app.include_router(settings.router)
app.include_router(status.router)
app.include_router(telegram.router)
app.include_router(history.router)


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok", "version": "1.0.1", "time": "2026-05-09T18:22:00Z"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
