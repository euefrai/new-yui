"""
Perfil de usuário da Yui (personalidade adaptativa).

Tabela no Supabase: users_profile
- id    : UUID (igual ao auth.users.id)
- email : texto
- nome  : opcional

Aqui tratamos apenas preferências simples que influenciam o tom da IA:
- nivel_tecnico       : "iniciante" | "intermediario" | "avancado"
- linguagens_pref     : lista/texto (ex: "python, js")
- modo_resposta       : "dev" | "explicativo" | "resumido"
"""

from typing import Dict, Optional

from core.supabase_client import supabase


def get_user_profile(user_id: str) -> Dict:
    """
    Busca perfil do usuário no Supabase.
    Se não existir ou Supabase estiver indisponível, retorna defaults seguros.
    """
    default = {
        "id": user_id,
        "email": "",
        "nivel_tecnico": "desconhecido",
        "linguagens_pref": "",
        "modo_resposta": "dev",
    }
    if not supabase or not user_id:
        return default
    try:
        res = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return default
        row = res.data[0]
        return {
            "id": row.get("id", user_id),
            "email": row.get("email") or "",
            "nivel_tecnico": (row.get("nivel_tecnico") or default["nivel_tecnico"]),
            "linguagens_pref": row.get("linguagens_pref") or "",
            "modo_resposta": row.get("modo_resposta") or default["modo_resposta"],
        }
    except Exception:
        return default


def upsert_user_profile(
    user_id: str,
    email: str = "",
    nivel_tecnico: Optional[str] = None,
    linguagens_pref: Optional[str] = None,
    modo_resposta: Optional[str] = None,
) -> bool:
    """Cria/atualiza perfil no Supabase. Retorna True em caso de sucesso."""
    if not supabase or not user_id:
        return False
    row: Dict[str, Optional[str]] = {
        "id": user_id,
        "email": email or None,
    }
    if nivel_tecnico:
        row["nivel_tecnico"] = nivel_tecnico
    if linguagens_pref:
        row["linguagens_pref"] = linguagens_pref
    if modo_resposta:
        row["modo_resposta"] = modo_resposta
    try:
        supabase.table("users_profile").upsert(row).execute()
        return True
    except Exception:
        return False

