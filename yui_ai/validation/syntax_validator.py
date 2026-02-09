"""
Validador de sintaxe para diferentes linguagens.
"""

import subprocess
import os
from typing import Dict, Optional, Tuple


def validar_sintaxe(arquivo: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Valida sintaxe de um arquivo.

    Retorna: (sucesso, saida, erro)
    """
    arquivo_abs = os.path.abspath(arquivo)

    if not os.path.exists(arquivo_abs):
        return False, None, f"Arquivo não encontrado: {arquivo_abs}"

    extensao = os.path.splitext(arquivo_abs)[1].lower()

    # Python
    if extensao == ".py":
        return _validar_python(arquivo_abs)

    # JavaScript/TypeScript
    if extensao in [".js", ".ts", ".jsx", ".tsx"]:
        return _validar_javascript(arquivo_abs)

    # Outras linguagens podem ser adicionadas aqui
    return True, "Validação de sintaxe não disponível para este tipo de arquivo", None


def _validar_python(arquivo: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Valida sintaxe Python usando compile()."""
    try:
        with open(arquivo, "r", encoding="utf-8", errors="replace") as f:
            codigo = f.read()

        compile(codigo, arquivo, "exec")
        return True, "Sintaxe Python válida", None

    except SyntaxError as e:
        erro_msg = f"Erro de sintaxe na linha {e.lineno}:\n{e.msg}\n"
        if e.text:
            erro_msg += f"  {e.text.strip()}\n"
            if e.offset:
                erro_msg += f"  {' ' * (e.offset - 1)}^\n"
        return False, None, erro_msg

    except Exception as e:
        return False, None, f"Erro ao validar sintaxe: {str(e)}"


def _validar_javascript(arquivo: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Valida sintaxe JavaScript usando node --check."""
    try:
        # Verifica se node está disponível
        resultado = subprocess.run(
            ["node", "--check", arquivo],
            capture_output=True,
            text=True,
            timeout=10
        )

        if resultado.returncode == 0:
            return True, "Sintaxe JavaScript válida", None
        else:
            return False, None, resultado.stderr or resultado.stdout or "Erro de sintaxe JavaScript"

    except FileNotFoundError:
        return True, "Node.js não encontrado - pulando validação de sintaxe", None
    except subprocess.TimeoutExpired:
        return False, None, "Timeout ao validar sintaxe JavaScript"
    except Exception as e:
        return True, f"Não foi possível validar sintaxe: {str(e)}", None
