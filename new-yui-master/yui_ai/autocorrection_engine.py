# autocorrection_engine.py

import json

from yui_ai.memory.memory import (
    obter_memoria,
    salvar_memoria
)

# =============================
# CHAVE/ASSINATURA DA SOLUÇÃO
# =============================
def _chave_solucao(acao: str, dados: dict | None) -> str:
    """
    Gera uma chave estável para não reaproveitar solução errada
    (ex.: "abrir_qualquer_coisa:brave" não pode valer para "whatsapp").
    """
    acao = (acao or "").strip()
    dados = dados or {}

    # Casos mais comuns: abrir algo
    if acao == "abrir_qualquer_coisa":
        alvo = str(dados.get("alvo", "") or "").strip().lower()
        return f"{acao}:{alvo}"

    if acao == "abrir_app":
        nome = str(dados.get("app") or dados.get("nome") or "").strip().lower()
        return f"{acao}:{nome}"

    # Default: json ordenado
    try:
        payload = json.dumps(dados, ensure_ascii=False, sort_keys=True)
    except Exception:
        payload = str(dados)
    return f"{acao}:{payload}"


# =============================
# BUSCAR SOLUÇÃO APRENDIDA
# =============================
def buscar_solucao(acao, dados=None):
    memoria = obter_memoria()
    solucoes = memoria.get("solucoes_aprendidas", {}) or {}

    chave = _chave_solucao(acao, dados or {})
    if chave in solucoes:
        return solucoes.get(chave)

    # compatibilidade com formato antigo (acao -> dados)
    antigo = solucoes.get(acao)
    if isinstance(antigo, dict) and antigo == (dados or {}):
        return antigo

    return None


# =============================
# SALVAR SOLUÇÃO FUNCIONAL
# =============================
def salvar_solucao(acao, dados):
    memoria = obter_memoria()

    # garante a chave
    if "solucoes_aprendidas" not in memoria:
        memoria["solucoes_aprendidas"] = {}

    chave = _chave_solucao(acao, dados)
    memoria["solucoes_aprendidas"][chave] = dados

    # ⚠️ salva a memória INTEIRA
    salvar_memoria(memoria)


# =============================
# GERAR ALTERNATIVA SIMPLES
# =============================
def gerar_alternativa(acao, dados):
    if acao == "abrir_app":
        return {
            "acao": "abrir_qualquer_coisa",
            "dados": {"alvo": dados.get("nome", "")}
        }

    return None
