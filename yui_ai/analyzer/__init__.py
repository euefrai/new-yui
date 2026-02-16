"""
Analisador técnico de projetos (somente leitura).

- Escaneia estrutura de pastas
- Mapeia arquivos e imports
- Detecta problemas arquiteturais
- Gera relatório técnico
- NUNCA altera código do projeto analisado
"""

from yui_ai.analyzer.report_builder import run_analysis

__all__ = ["run_analysis"]
