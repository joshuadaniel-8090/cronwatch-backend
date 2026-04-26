# Cronwatch Backend (Supabase Auth)

Cronwatch is a SaaS cron job monitoring tool built with FastAPI and Supabase. Authentication is handled entirely by Supabase Auth.

## Tech Stack
- **Framework:** FastAPI
- **Database:** Supabase (PostgreSQL) + SQLAlchemy 2.0
- **Auth:** Supabase Auth (JWT Verification)
- **Migrations:** Alembic
- **Background Jobs:** APScheduler
- **Alerts:** Telegram (httpx) + Email (Resend)

## Prerequisites
- Python 3.11+
- Supabase Account
- Telegram Bot (via @BotFather)
- Resend Account (for email alerts)

## Setup

1. **Clone the repository**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Supabase Configuration:**
   - Create a new project on Supabase.
   - Enable Email + Google OAuth in the Supabase Auth dashboard.
   - Find your **JWT Secret**: Settings → API → JWT Secret.
   - Find your **DATABASE_URL**: Settings → Database → URI (use the Connection String with mode=transaction or session, ensuring sslmode=require).

4. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`
   - Fill in your Supabase variables: `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, etc.
   - Fill in your Telegram Bot Token and Resend API Key.

5. **Run Database Migrations:**
   ```bash
   alembic revision --autogenerate -m "initial migration"
   alembic upgrade head
   ```

6. **Start the Server:**
   ```bash
   uvicorn app.main:app --reload
   ```

## Features
- **Supabase Auth**: FastAPI verifies tokens from Supabase; no custom user management code.
- **Pings**: Cron jobs send GET requests to `/ping/{token}` (no auth required).
- **Monitoring**: Detects missed pings based on interval + grace period.
- **Alerting**: Notifies via Telegram and Email when a job fails.
- **Dashboard API**: Manage monitors and view ping history.
- **Status Pages**: Publicly shareable status pages for your cron jobs.

## Free Plan Limits
- Maximum 3 monitors per user. Profile is auto-created on the first authenticated request.
