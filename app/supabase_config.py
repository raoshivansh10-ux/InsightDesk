import os
import logging
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "your-anon-key")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "your-service-role-key")

# Check if placeholders or missing
is_configured = (
    SUPABASE_URL != "https://your-project.supabase.co" and
    SUPABASE_ANON_KEY != "your-anon-key" and
    SUPABASE_URL is not None and
    SUPABASE_ANON_KEY is not None
)

supabase = None
supabase_admin = None

if is_configured:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        if SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_KEY != "your-service-role-key":
            supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        else:
            supabase_admin = supabase
        logging.info("Supabase client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}")
else:
    logging.warning("Supabase environment variables not configured or using placeholders. Supabase client will be initialized as None.")
