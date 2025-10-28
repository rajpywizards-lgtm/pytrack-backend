import os
from supabase import create_client, Client
from app.core.env import require  # <-- loads .env on import

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

require(["SUPABASE_URL", "SUPABASE_ANON_KEY"])  # fast fail for the obvious two
if not SUPABASE_SERVICE_ROLE:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE (or SUPABASE_SERVICE_ROLE_KEY)")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
