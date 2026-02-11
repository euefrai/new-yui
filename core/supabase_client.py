"""
Cliente Supabase para auth e persistência de chats (backend).
Usa sempre SUPABASE_SERVICE_KEY (nunca anon no servidor).
"""
from config.settings import SUPABASE_KEY_BACKEND, SUPABASE_URL

supabase = None
if SUPABASE_URL and SUPABASE_KEY_BACKEND:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY_BACKEND)
    except Exception:
        supabase = None
