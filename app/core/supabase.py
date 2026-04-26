from supabase import create_client, Client
from app.core.config import settings

# Service role client — used for all backend operations
# This bypasses Row Level Security — safe for server-side use only
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)
