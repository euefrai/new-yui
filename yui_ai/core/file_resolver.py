"""
File Resolver inteligente.

- Normaliza nomes de arquivos ("arquivo utils.py" → "utils.py").
- Busca arquivos recursivamente no projeto.
- Retorna o caminho real ou None.
- Nunca assume que o usuário fornece caminho exato.
"""

import os
import re
from typing import Optional

# Raiz do projeto: pasta que contém yui_ai/
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_DIR = os.path.dirname(_CORE_DIR)
PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)


def normalizar_nome_arquivo(entrada: str) -> str:
    """
    Normaliza a string que o usuário disse como nome de arquivo.

    - "arquivo utils.py" → "utils.py"
    - "o arquivo utils.py" → "utils.py"
    - "  utils.py  " → "utils.py"
    - "arquivo config/settings.py" → "config/settings.py"
    """
    if not entrada or not isinstance(entrada, str):
        return ""
    s = entrada.strip().strip('"').strip("'")
    # Remove prefixos comuns em linguagem natural
    prefixos = [
        r"^(?:o|a|um|uma)\s+arquivo\s+",
        r"^arquivo\s+",
        r"^o\s+",
        r"^arquivo\s+de\s+",
        r"^(?:no|em|do|da)\s+arquivo\s+",
    ]
    for pat in prefixos:
        s = re.sub(pat, "", s, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", s).strip()


def resolver_arquivo(
    entrada: str,
    raiz: Optional[str] = None,
    extensoes_preferidas: Optional[list] = None,
) -> Optional[str]:
    """
    Resolve uma string de entrada para um caminho real de arquivo.

    - Se entrada já for caminho absoluto e existir, retorna normalizado.
    - Se for caminho relativo existente a partir de raiz (ou PROJECT_ROOT), retorna absoluto.
    - Caso contrário, busca recursivamente por nome de arquivo (e opcionalmente extensão).

    Retorna caminho absoluto do arquivo ou None se não encontrar.
    """
    if not entrada or not isinstance(entrada, str):
        return None

    base = (raiz or PROJECT_ROOT).strip()
    if not os.path.isdir(base):
        return None

    nome_normalizado = normalizar_nome_arquivo(entrada)
    if not nome_normalizado:
        return None

    # 1) Caminho absoluto já existente
    if os.path.isabs(nome_normalizado) and os.path.isfile(nome_normalizado):
        return os.path.normpath(os.path.abspath(nome_normalizado))

    # 2) Caminho relativo a partir da raiz
    candidato_rel = os.path.normpath(os.path.join(base, nome_normalizado))
    if os.path.isfile(candidato_rel):
        return os.path.abspath(candidato_rel)

    # 3) Apenas nome de arquivo (ex: "utils.py") → busca recursiva
    nome_base = os.path.basename(nome_normalizado)
    if not nome_base:
        return None

    extensoes = extensoes_preferidas or [".py", ".js", ".ts", ".json", ".md", ".txt", ""]
    # Garante que temos pelo menos a extensão atual do nome
    ext = os.path.splitext(nome_base)[1].lower()
    if ext and ext not in extensoes:
        extensoes = [ext] + [e for e in extensoes if e != ext]

    for _dir, _dirnames, filenames in os.walk(base):
        for f in filenames:
            if f == nome_base:
                path = os.path.join(_dir, f)
                if os.path.isfile(path):
                    return os.path.abspath(path)
            # Match sem extensão: ex. "utils" → utils.py
            if not ext and os.path.splitext(f)[0] == nome_base:
                for e in extensoes:
                    if e and f.endswith(e):
                        path = os.path.join(_dir, f)
                        if os.path.isfile(path):
                            return os.path.abspath(path)
                        break

    return None


def validar_arquivo_para_edicao(entrada: str, raiz: Optional[str] = None) -> tuple[bool, Optional[str], str]:
    """
    Valida se existe um arquivo editável correspondente à entrada.

    Retorna: (sucesso, caminho_absoluto, mensagem_erro)
    - sucesso=True e caminho preenchido → arquivo encontrado.
    - sucesso=False, caminho=None, mensagem_erro → mensagem amigável para o usuário.
    """
    caminho = resolver_arquivo(entrada, raiz=raiz)
    if caminho:
        return True, caminho, ""
    nome = normalizar_nome_arquivo(entrada) or entrada.strip() or "arquivo"
    return False, None, f"Não encontrei o arquivo '{nome}' no projeto. Verifique o nome ou o caminho."
