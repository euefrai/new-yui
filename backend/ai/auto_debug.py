# ==========================================================
# YUI AUTO DEBUG AGENT
# Detecta erros em código e tenta corrigir automaticamente.
# Middleware: resposta → falhou? → analisar traceback → correção.
# ==========================================================

import json
import re
from typing import Callable, List, Tuple


def detectar_stacktrace(texto: str) -> bool:
    """Detecta se existe erro técnico / stacktrace na resposta."""
    if not texto or not texto.strip():
        return False
    padroes = [
        r"Traceback \(most recent call last\):",
        r"Error:",
        r"Exception:",
        r"SyntaxError:",
        r"TypeError:",
        r"ReferenceError",
        r"Undefined",
        r"NameError:",
        r"ValueError:",
        r"IndexError:",
        r"File \"",
        r"  File \"",
        r"^\s*line \d+",
        r"RuntimeError:",
    ]
    for p in padroes:
        if re.search(p, texto, re.IGNORECASE | re.MULTILINE):
            return True
    return False


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


def auto_debug(
    model_call: Callable[[List[dict]], str],
    resposta_original: str,
) -> Tuple[bool, str]:
    """
    Se a resposta contiver stacktrace/erro técnico, pede ao modelo para corrigir.

    - model_call: função que recebe lista de mensagens e retorna o texto da resposta.
    - resposta_original: texto gerado pela IA (pode conter código com erro).

    Retorna (True, nova_resposta) se corrigiu, ou (False, resposta_original) caso contrário.
    """
    if not detectar_stacktrace(resposta_original):
        return False, resposta_original

    prompt_debug = [
        {
            "role": "system",
            "content": """
Você é o módulo AUTO DEBUG da YUI.

Sua função:
- analisar o erro técnico presente no texto
- corrigir o código
- devolver a versão corrigida e funcional

Responda SOMENTE em JSON:

{"corrigido": true, "nova_resposta": "código ou texto corrigido aqui"}
""",
        },
        {
            "role": "user",
            "content": f"""
Analise e corrija este conteúdo:

{resposta_original}
""",
        },
    ]

    try:
        resultado = model_call(prompt_debug)
        if not resultado or not resultado.strip():
            return False, resposta_original

        dados = _extrair_json(resultado)
        if not dados or not dados.get("corrigido"):
            return False, resposta_original

        nova = (dados.get("nova_resposta") or "").strip()
        if nova:
            return True, nova
        return False, resposta_original
    except Exception:
        return False, resposta_original


def analisar_traceback(
    model_call: Callable[[List[dict]], str],
    traceback_str: str,
) -> Tuple[bool, str]:
    """
    Analisa um traceback e sugere correção (middleware para exceções).
    Útil quando executar falha: try/except chama analisar_traceback(traceback).
    Retorna (True, sugestao) ou (False, traceback_original).
    """
    if not traceback_str or not traceback_str.strip():
        return False, traceback_str

    prompt = [
        {
            "role": "system",
            "content": "Você é o módulo AUTO DEBUG da YUI. Analise o traceback e sugira a correção. "
            "Responda em JSON: {\"corrigido\": true, \"sugestao\": \"texto da correção\"}",
        },
        {"role": "user", "content": f"Traceback:\n\n{traceback_str}"},
    ]

    try:
        resultado = model_call(prompt)
        if not resultado or not resultado.strip():
            return False, traceback_str
        dados = _extrair_json(resultado)
        if not dados or not dados.get("corrigido"):
            return False, traceback_str
        sugestao = (dados.get("sugestao") or "").strip()
        return (True, sugestao) if sugestao else (False, traceback_str)
    except Exception:
        return False, traceback_str
