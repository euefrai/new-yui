"""
Executor de linters.

Detecta e executa linters se existirem.
"""

import subprocess
import os
from typing import Dict, List, Optional, Tuple


def executar_linter(arquivo_modificado: Optional[str] = None, diretorio_projeto: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """
    Executa linter se existir.

    Retorna: (sucesso, saida, erro, detalhes)
    detalhes = {
        "linter": str,  # pylint, flake8, eslint, etc.
        "erros": int,
        "avisos": int
    }
    """
    # Determina diretório do projeto
    if diretorio_projeto:
        raiz = os.path.abspath(diretorio_projeto)
    elif arquivo_modificado:
        raiz = os.path.dirname(os.path.abspath(arquivo_modificado))
        # Tenta subir até encontrar diretório raiz do projeto
        while raiz != os.path.dirname(raiz):
            if any(os.path.exists(os.path.join(raiz, f)) for f in [".pylintrc", ".flake8", ".eslintrc", "pyproject.toml", "package.json"]):
                break
            raiz = os.path.dirname(raiz)
    else:
        raiz = os.getcwd()

    extensao = os.path.splitext(arquivo_modificado or "")[1].lower() if arquivo_modificado else ""

    # Python
    if extensao == ".py" or not extensao:
        # Tenta pylint primeiro
        if _tem_pylint(raiz):
            return _executar_pylint(arquivo_modificado or raiz, raiz)

        # Tenta flake8
        if _tem_flake8(raiz):
            return _executar_flake8(arquivo_modificado or raiz, raiz)

    # JavaScript/TypeScript
    if extensao in [".js", ".ts", ".jsx", ".tsx"]:
        if _tem_eslint(raiz):
            return _executar_eslint(arquivo_modificado or raiz, raiz)

    # Nenhum linter detectado
    return True, "Nenhum linter detectado", None, {
        "linter": "nenhum",
        "erros": 0,
        "avisos": 0
    }


def _tem_pylint(raiz: str) -> bool:
    """Verifica se pylint está disponível."""
    return _tem_comando("pylint")


def _tem_flake8(raiz: str) -> bool:
    """Verifica se flake8 está disponível."""
    return _tem_comando("flake8")


def _tem_eslint(raiz: str) -> bool:
    """Verifica se eslint está disponível."""
    return _tem_comando("eslint") or os.path.exists(os.path.join(raiz, "node_modules", ".bin", "eslint"))


def _tem_comando(comando: str) -> bool:
    """Verifica se comando está disponível."""
    try:
        subprocess.run(
            [comando, "--version"],
            capture_output=True,
            timeout=2
        )
        return True
    except Exception:
        return False


def _executar_pylint(arquivo: str, raiz: str) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Executa pylint."""
    try:
        cmd = ["pylint", arquivo, "--output-format=text"]
        
        resultado = subprocess.run(
            cmd,
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=30
        )

        saida = resultado.stdout + resultado.stderr
        
        # Parse básico
        erros = saida.count("error")
        avisos = saida.count("warning")
        
        # pylint retorna 0 se não houver erros críticos
        sucesso = resultado.returncode in [0, 4]  # 4 = alguns avisos mas sem erros críticos

        return sucesso, saida, None if sucesso else saida, {
            "linter": "pylint",
            "erros": erros,
            "avisos": avisos
        }

    except FileNotFoundError:
        return True, "pylint não encontrado", None, {"linter": "pylint", "erros": 0, "avisos": 0}
    except subprocess.TimeoutExpired:
        return False, None, "Timeout ao executar pylint", {"linter": "pylint", "erros": 0, "avisos": 0}
    except Exception as e:
        return False, None, f"Erro ao executar pylint: {str(e)}", {"linter": "pylint", "erros": 0, "avisos": 0}


def _executar_flake8(arquivo: str, raiz: str) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Executa flake8."""
    try:
        resultado = subprocess.run(
            ["flake8", arquivo],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=30
        )

        saida = resultado.stdout + resultado.stderr
        sucesso = resultado.returncode == 0

        # Parse básico
        linhas_erro = [l for l in saida.split("\n") if l.strip()]
        erros = len(linhas_erro)

        return sucesso, saida, None if sucesso else saida, {
            "linter": "flake8",
            "erros": erros,
            "avisos": 0
        }

    except FileNotFoundError:
        return True, "flake8 não encontrado", None, {"linter": "flake8", "erros": 0, "avisos": 0}
    except Exception as e:
        return False, None, f"Erro ao executar flake8: {str(e)}", {"linter": "flake8", "erros": 0, "avisos": 0}


def _executar_eslint(arquivo: str, raiz: str) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Executa eslint."""
    try:
        # Tenta usar npx se disponível
        cmd = ["npx", "eslint", arquivo] if _tem_comando("npx") else ["eslint", arquivo]

        resultado = subprocess.run(
            cmd,
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=30
        )

        saida = resultado.stdout + resultado.stderr
        sucesso = resultado.returncode == 0

        # Parse básico
        erros = saida.count("error")
        avisos = saida.count("warning")

        return sucesso, saida, None if sucesso else saida, {
            "linter": "eslint",
            "erros": erros,
            "avisos": avisos
        }

    except FileNotFoundError:
        return True, "eslint não encontrado", None, {"linter": "eslint", "erros": 0, "avisos": 0}
    except Exception as e:
        return False, None, f"Erro ao executar eslint: {str(e)}", {"linter": "eslint", "erros": 0, "avisos": 0}
