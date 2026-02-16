"""
Reexporta o cliente Supabase do core (backend usa SUPABASE_SERVICE_KEY).
Variáveis: SUPABASE_URL, SUPABASE_ANON_KEY (frontend), SUPABASE_SERVICE_KEY (backend).
"""
from core.supabase_client import supabase

__all__ = ["supabase"]
