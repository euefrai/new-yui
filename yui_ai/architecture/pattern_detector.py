"""
Detector de padrões arquiteturais no código.

Analisa código e sugere padrões para registro.
"""

import os
import re
from typing import Dict, List, Optional


class PatternDetector:
    """
    Detecta padrões arquiteturais em código existente.
    """

    def detectar_padroes_arquivo(self, arquivo: str) -> List[Dict]:
        """
        Detecta padrões em um arquivo específico.

        Retorna: lista de padrões detectados
        """
        if not os.path.exists(arquivo):
            return []

        try:
            with open(arquivo, "r", encoding="utf-8", errors="replace") as f:
                conteudo = f.read()

            padroes = []

            # Detecta padrões Python
            if arquivo.endswith(".py"):
                padroes.extend(self._detectar_padroes_python(conteudo, arquivo))

            # Detecta padrões JavaScript/TypeScript
            if arquivo.endswith((".js", ".ts", ".jsx", ".tsx")):
                padroes.extend(self._detectar_padroes_javascript(conteudo, arquivo))

            return padroes

        except Exception:
            return []

    def _detectar_padroes_python(self, conteudo: str, arquivo: str) -> List[Dict]:
        """Detecta padrões específicos de Python."""
        padroes = []

        # Type hints
        if re.search(r"def\s+\w+\s*\([^)]*:\s*\w+", conteudo):
            padroes.append({
                "nome": "Type Hints",
                "descricao": "Funções usam type hints",
                "quando_usar": "Sempre que possível para melhorar legibilidade",
                "exemplo": "def calcular_total(items: List[float]) -> float:"
            })

        # Docstrings
        if re.search(r'def\s+\w+.*?\n\s+""".*?"""', conteudo, re.DOTALL):
            padroes.append({
                "nome": "Docstrings",
                "descricao": "Funções têm docstrings",
                "quando_usar": "Sempre documentar funções públicas",
                "exemplo": 'def calcular_total(...):\n    """Calcula total de items."""'
            })

        # Classes
        if re.search(r"class\s+\w+", conteudo):
            padroes.append({
                "nome": "Orientação a Objetos",
                "descricao": "Uso de classes",
                "quando_usar": "Para modelar entidades com estado",
                "exemplo": "class User:\n    def __init__(self, name): ..."
            })

        # Decorators
        if re.search(r"@\w+", conteudo):
            padroes.append({
                "nome": "Decorators",
                "descricao": "Uso de decorators",
                "quando_usar": "Para adicionar funcionalidade sem modificar função",
                "exemplo": "@property\ndef nome(self): ..."
            })

        return padroes

    def _detectar_padroes_javascript(self, conteudo: str, arquivo: str) -> List[Dict]:
        """Detecta padrões específicos de JavaScript/TypeScript."""
        padroes = []

        # Arrow functions
        if re.search(r"=>\s*{", conteudo):
            padroes.append({
                "nome": "Arrow Functions",
                "descricao": "Uso de arrow functions",
                "quando_usar": "Para funções curtas e callbacks",
                "exemplo": "const calcular = (x, y) => x + y"
            })

        # Classes ES6
        if re.search(r"class\s+\w+", conteudo):
            padroes.append({
                "nome": "Classes ES6",
                "descricao": "Uso de classes ES6",
                "quando_usar": "Para modelar entidades",
                "exemplo": "class User {\n  constructor(name) { ... }\n}"
            })

        # Async/await
        if re.search(r"async\s+function|await\s+", conteudo):
            padroes.append({
                "nome": "Async/Await",
                "descricao": "Uso de async/await",
                "quando_usar": "Para operações assíncronas",
                "exemplo": "async function buscarDados() {\n  const data = await fetch(...)\n}"
            })

        return padroes
