"""
Executor de ferramentas (tools) registradas.

Fornece uma API simples para o backend:
- run_tool(name, args) -> dict
"""

from typing import Any, Dict

from core.tools_registry import get_tool


def run_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executa uma ferramenta registrada pelo nome.

    Retorno padronizado:
        {
          "ok": bool,
          "result": any | None,
          "error": str | None,
        }
    """
    tool = get_tool(name)
    if not tool:
        return {"ok": False, "result": None, "error": f"Ferramenta '{name}' não encontrada."}
    fn = tool.get("fn")
    if not fn:
        return {"ok": False, "result": None, "error": f"Ferramenta '{name}' não possui função associada."}

    try:
        result = fn(**(args or {}))
        return {"ok": True, "result": result, "error": None}
    except TypeError as e:
        # Erro comum: parâmetros faltando ou nomes errados
        return {"ok": False, "result": None, "error": f"Erro de parâmetros ao chamar '{name}': {e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "result": None, "error": str(e)}

