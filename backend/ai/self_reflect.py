# ==========================================================
# YUI SELF REFLECT SYSTEM
# A IA analisa a própria resposta e melhora automaticamente
# ==========================================================

import json
from typing import Callable, List, Tuple


def _extrair_json(texto: str) -> dict | None:
    """Extrai um objeto JSON do texto (pode vir com markdown ou texto ao redor)."""
    if not texto or not texto.strip():
        return None
    s = texto.strip()
    for marker in ("```json", "```"):
        if marker in s:
            i = s.find(marker)
            s = s[i + len(marker) :].strip()
            if s.endswith("```"):
                s = s[: s.rfind("```")].strip()
            break
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = None
    escape = False
    end = -1
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if in_string:
            if c == in_string:
                in_string = None
            continue
        if c in ('"', "'"):
            in_string = c
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        end = s.rfind("}")
    if end == -1 or end < start:
        return None
    try:
        return json.loads(s[start : end + 1])
    except Exception:
        return None


def avaliar_resposta(
    model_call: Callable[[List[dict]], str],
    mensagens: List[dict],
    resposta_original: str,
) -> Tuple[bool, str]:
    """
    A IA analisa a própria resposta e decide se está ok ou se deve melhorar.

    - model_call: função que recebe lista de mensagens e retorna o texto da resposta (ex.: call OpenAI).
    - mensagens: histórico da conversa (pode ser usado em versões futuras).
    - resposta_original: resposta gerada pela IA.

    Retorna (True, nova_resposta) se melhorou, ou (False, resposta_original) se manteve.
    """
    if not resposta_original or not resposta_original.strip():
        return False, resposta_original

    prompt_reflexao = [
        {
            "role": "system",
            "content": """
Você é um módulo crítico da YUI.

Sua função:
- analisar a resposta gerada
- detectar erros técnicos
- detectar respostas vagas ou fracas
- melhorar a clareza e utilidade

Se a resposta estiver boa, retorne:

{"status":"ok"}

Se precisar melhorar, retorne:

{"status":"melhorar","nova_resposta":"texto melhorado aqui"}

Responda SOMENTE em JSON.
""",
        },
        {
            "role": "user",
            "content": f"""
Resposta original da IA:

{resposta_original}
""",
        },
    ]

    try:
        reflexao = model_call(prompt_reflexao)
        if not reflexao or not reflexao.strip():
            return False, resposta_original

        dados = _extrair_json(reflexao)
        if not dados:
            return False, resposta_original

        if dados.get("status") == "melhorar":
            nova = (dados.get("nova_resposta") or "").strip()
            if nova:
                return True, nova
        return False, resposta_original
    except Exception:
        return False, resposta_original
