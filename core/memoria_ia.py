"""
Memória de longo prazo (RAG): resumos de decisões e conclusões do projeto.
Usada pelo Heathcliff para lembrar decisões anteriores.
"""

import json
import re
from pathlib import Path
from typing import List, Optional

try:
    from core.supabase_client import supabase
except ImportError:
    supabase = None

try:
    from config import settings
    MEMORIA_IA_PATH = Path(settings.DATA_DIR) / "memoria_ia.json"
except Exception:
    MEMORIA_IA_PATH = Path(__file__).resolve().parents[1] / "data" / "memoria_ia.json"


def _load_local() -> list:
    """Carrega memória local (fallback quando Supabase não disponível)."""
    MEMORIA_IA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORIA_IA_PATH.exists():
        return []
    try:
        with open(MEMORIA_IA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_local(items: list) -> None:
    """Salva memória local."""
    MEMORIA_IA_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Manter últimos 500 registros
    items = items[-500:]
    with open(MEMORIA_IA_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def salvar_resumo(
    user_id: str,
    resumo: str,
    tags: str = "",
    chat_id: Optional[str] = None,
) -> bool:
    """
    Salva um resumo de decisão ou conclusão na memória de longo prazo.
    tags: string separada por vírgula, ex: "#estilo,#db,#login"
    """
    if not resumo or not resumo.strip():
        return False
    tags = (tags or "").strip()
    if supabase:
        try:
            row = {
                "user_id": user_id,
                "resumo": resumo.strip()[:4000],
                "tags": tags,
            }
            if chat_id:
                row["chat_id"] = chat_id
            supabase.table("memoria_ia").insert(row).execute()
            return True
        except Exception:
            pass
    # Fallback JSON local
    items = _load_local()
    items.append({
        "id": str(len(items)),
        "user_id": user_id,
        "chat_id": chat_id,
        "resumo": resumo.strip()[:4000],
        "tags": tags,
        "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    })
    _save_local(items)
    return True


def buscar_memoria(
    user_id: str,
    query: str = "",
    chat_id: Optional[str] = None,
    limite: int = 10,
) -> str:
    """
    Busca resumos relevantes na memória do usuário.
    Retorna texto formatado para incluir no contexto do Heathcliff.
    """
    if supabase:
        try:
            q = supabase.table("memoria_ia").select("resumo,tags,created_at,chat_id").eq("user_id", user_id)
            rows = q.order("created_at", desc=True).limit(limite * 3).execute()
            raw = rows.data or []
            if chat_id:
                items = [x for x in raw if x.get("chat_id") == chat_id or not x.get("chat_id")][:limite * 2]
            else:
                items = raw[:limite * 2]
        except Exception:
            items = []
    else:
        items = _load_local()
        items = [x for x in items if x.get("user_id") == user_id]
        if chat_id:
            items = [x for x in items if x.get("chat_id") == chat_id or not x.get("chat_id")]
        items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)[:limite * 2]
    if not items:
        return ""
    # Filtro por query (tags ou palavras-chave)
    if query:
        q_lower = query.lower()
        kw = set(re.findall(r"#?\w+", q_lower))
        scored = []
        for it in items:
            resumo = (it.get("resumo") or "").lower()
            tags_str = (it.get("tags") or "").lower()
            score = 0
            for w in kw:
                if w in resumo or w in tags_str:
                    score += 1
            scored.append((score, it))
        scored.sort(key=lambda x: -x[0])
        items = [x[1] for x in scored if x[0] > 0][:limite]
    else:
        items = items[:limite]
    lines = []
    for it in items:
        r = (it.get("resumo") or "").strip()
        t = (it.get("tags") or "").strip()
        if r:
            lines.append(f"- {r}" + (f" [{t}]" if t else ""))
    if not lines:
        return ""
    return "MEMÓRIA DE DECISÕES ANTERIORES DO PROJETO:\n\n" + "\n".join(lines)
