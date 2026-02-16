"""
Executor de testes automatizados.

Detecta e executa testes se existirem.
"""

import subprocess
import os
from typing import Dict, List, Optional, Tuple


def executar_testes(arquivo_modificado: Optional[str] = None, diretorio_projeto: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """
    Executa testes se existirem.

    Retorna: (sucesso, saida, erro, detalhes)
    detalhes = {
        "framework": str,  # pytest, unittest, jest, etc.
        "testes_executados": int,
        "testes_passaram": int,
        "testes_falharam": int
    }
    """
    # Determina diretório do projeto
    if diretorio_projeto:
        raiz = os.path.abspath(diretorio_projeto)
    elif arquivo_modificado:
        raiz = os.path.dirname(os.path.abspath(arquivo_modificado))
        # Tenta subir até encontrar diretório raiz do projeto
        while raiz != os.path.dirname(raiz):
            if any(os.path.exists(os.path.join(raiz, f)) for f in ["pytest.ini", "setup.py", "requirements.txt", "package.json", "pyproject.toml"]):
                break
            raiz = os.path.dirname(raiz)
    else:
        raiz = os.getcwd()

    # Tenta detectar framework de testes
    # Python: pytest ou unittest
    if _tem_pytest(raiz):
        return _executar_pytest(raiz, arquivo_modificado)

    if _tem_unittest(raiz):
        return _executar_unittest(raiz, arquivo_modificado)

    # JavaScript: jest, mocha, etc.
    if _tem_jest(raiz):
        return _executar_jest(raiz)

    # Nenhum framework detectado
    return True, "Nenhum framework de testes detectado", None, {
        "framework": "nenhum",
        "testes_executados": 0,
        "testes_passaram": 0,
        "testes_falharam": 0
    }


def _tem_pytest(raiz: str) -> bool:
    """Verifica se projeto usa pytest."""
    return (
        os.path.exists(os.path.join(raiz, "pytest.ini")) or
        os.path.exists(os.path.join(raiz, "pyproject.toml")) or
        _tem_comando("pytest")
    )


def _tem_unittest(raiz: str) -> bool:
    """Verifica se projeto usa unittest."""
    # Procura por arquivos de teste
    for root, dirs, files in os.walk(raiz):
        if any(f.startswith("test_") and f.endswith(".py") for f in files):
            return True
    return False


def _tem_jest(raiz: str) -> bool:
    """Verifica se projeto usa Jest."""
    return (
        os.path.exists(os.path.join(raiz, "package.json")) and
        _tem_comando("jest")
    )


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


def _executar_pytest(raiz: str, arquivo_modificado: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Executa testes com pytest."""
    try:
        cmd = ["pytest", "-v", "--tb=short"]
        
        # Se arquivo específico foi modificado, roda apenas testes relacionados
        if arquivo_modificado:
            # Tenta encontrar teste correspondente
            nome_base = os.path.splitext(os.path.basename(arquivo_modificado))[0]
            teste_candidato = os.path.join(os.path.dirname(arquivo_modificado), f"test_{nome_base}.py")
            if os.path.exists(teste_candidato):
                cmd.append(teste_candidato)

        resultado = subprocess.run(
            cmd,
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Parse da saída do pytest
        saida = resultado.stdout + resultado.stderr
        testes_passaram = saida.count("PASSED")
        testes_falharam = saida.count("FAILED") + saida.count("ERROR")

        sucesso = resultado.returncode == 0

        return sucesso, saida, None if sucesso else saida, {
            "framework": "pytest",
            "testes_executados": testes_passaram + testes_falharam,
            "testes_passaram": testes_passaram,
            "testes_falharam": testes_falharam
        }

    except FileNotFoundError:
        return True, "pytest não encontrado", None, {"framework": "pytest", "testes_executados": 0, "testes_passaram": 0, "testes_falharam": 0}
    except subprocess.TimeoutExpired:
        return False, None, "Timeout ao executar testes (limite: 60s)", {"framework": "pytest", "testes_executados": 0, "testes_passaram": 0, "testes_falharam": 0}
    except Exception as e:
        return False, None, f"Erro ao executar pytest: {str(e)}", {"framework": "pytest", "testes_executados": 0, "testes_passaram": 0, "testes_falharam": 0}


def _executar_unittest(raiz: str, arquivo_modificado: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Executa testes com unittest."""
    try:
        cmd = ["python", "-m", "unittest", "discover", "-v"]

        resultado = subprocess.run(
            cmd,
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=60
        )

        saida = resultado.stdout + resultado.stderr
        sucesso = resultado.returncode == 0

        # Parse básico
        testes_passaram = saida.count("ok")
        testes_falharam = saida.count("FAILED") + saida.count("ERROR")

        return sucesso, saida, None if sucesso else saida, {
            "framework": "unittest",
            "testes_executados": testes_passaram + testes_falharam,
            "testes_passaram": testes_passaram,
            "testes_falharam": testes_falharam
        }

    except Exception as e:
        return False, None, f"Erro ao executar unittest: {str(e)}", {"framework": "unittest", "testes_executados": 0, "testes_passaram": 0, "testes_falharam": 0}


def _executar_jest(raiz: str) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Executa testes com Jest."""
    try:
        resultado = subprocess.run(
            ["npm", "test", "--", "--verbose"],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=60
        )

        saida = resultado.stdout + resultado.stderr
        sucesso = resultado.returncode == 0

        # Parse básico
        testes_passaram = saida.count("PASS")
        testes_falharam = saida.count("FAIL")

        return sucesso, saida, None if sucesso else saida, {
            "framework": "jest",
            "testes_executados": testes_passaram + testes_falharam,
            "testes_passaram": testes_passaram,
            "testes_falharam": testes_falharam
        }

    except Exception as e:
        return False, None, f"Erro ao executar jest: {str(e)}", {"framework": "jest", "testes_executados": 0, "testes_passaram": 0, "testes_falharam": 0}
