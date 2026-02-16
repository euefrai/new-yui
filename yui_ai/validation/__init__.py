"""
Sistema de validação automática pós-edição.

Executa APÓS aplicar código:
- Verificação de sintaxe
- Execução de testes (se existirem)
- Execução de linter (se existir)

NUNCA corrige automaticamente - apenas relata e pergunta.
"""

from yui_ai.validation.syntax_validator import validar_sintaxe
from yui_ai.validation.test_runner import executar_testes
from yui_ai.validation.linter_runner import executar_linter
from yui_ai.validation.validation_engine import ValidationEngine

__all__ = [
    "validar_sintaxe",
    "executar_testes",
    "executar_linter",
    "ValidationEngine"
]
