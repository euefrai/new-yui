# ==========================================================
# YUI AUTO SKILL SYSTEM
# Sistema dinâmico de habilidades: descobre, registra e executa.
# ==========================================================

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

# Pasta de skills ao lado deste módulo
_BASE = Path(__file__).resolve().parent
PASTA_SKILLS = str(_BASE / "skills")
SKILL_INDEX = str(_BASE / "skills" / "index.json")

if not os.path.exists(PASTA_SKILLS):
    os.makedirs(PASTA_SKILLS)


# ==========================================================
# GARANTE INDEX
# ==========================================================

def carregar_index() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(SKILL_INDEX):
        with open(SKILL_INDEX, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(SKILL_INDEX, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_index(data: Dict[str, Any]) -> None:
    with open(SKILL_INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ==========================================================
# REGISTRAR SKILL
# ==========================================================

def registrar_skill(nome: str, descricao: str, arquivo: str) -> None:
    """Registra uma nova skill no index (nome, descrição, nome do arquivo .py)."""
    index = carregar_index()
    index[nome] = {
        "descricao": descricao,
        "arquivo": arquivo,
        "criado_em": datetime.now().isoformat(),
    }
    salvar_index(index)


# ==========================================================
# LISTAR SKILLS
# ==========================================================

def listar_skills() -> Dict[str, Dict[str, Any]]:
    """Retorna o index de skills: { nome: { descricao, arquivo, criado_em } }."""
    return carregar_index()


# ==========================================================
# EXECUTAR SKILL
# ==========================================================

def executar_skill(nome: str, dados: Dict[str, Any] | None = None) -> Tuple[bool, Any]:
    """
    Executa a skill pelo nome. O arquivo da skill deve definir uma função run(dados).
    Retorna (True, resultado) ou (False, mensagem_de_erro).
    """
    index = carregar_index()
    if nome not in index:
        return False, f"Skill '{nome}' não encontrada"

    arquivo = index[nome]["arquivo"]
    caminho = os.path.join(PASTA_SKILLS, arquivo)

    if not os.path.exists(caminho):
        return False, "Arquivo da skill não existe"

    try:
        namespace: Dict[str, Any] = {}
        with open(caminho, "r", encoding="utf-8") as f:
            codigo = f.read()
        exec(codigo, namespace)

        if "run" in namespace:
            resultado = namespace["run"](dados or {})
            return True, resultado
        return False, "Skill não possui função run()"
    except Exception as e:
        return False, str(e)
