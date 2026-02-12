"""
Executor de ferramentas (tools) registradas.

Fornece uma API simples para o backend:
- run_tool(name, args) -> dict

Identity-aware: valida ação antes de executar.
"""

from typing import Any, Dict

from core.tools_registry import get_tool

try:
    from core.identity_core import get_identity_core
except ImportError:
    get_identity_core = None
try:
    from core.metacognition import record_action
except ImportError:
    record_action = lambda _: None


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
    if get_identity_core:
        identity = get_identity_core()
        ok, motivo = identity.validate("execute", tool_name=name, args=args)
        if not ok:
            return {"ok": False, "result": None, "error": motivo or "Ação bloqueada pela identidade."}

    tool = get_tool(name)
    if not tool:
        try:
            from core.plugins_loader import ensure_plugins_loaded
            ensure_plugins_loaded()
            tool = get_tool(name)
        except Exception:
            pass
    if not tool:
        return {"ok": False, "result": None, "error": f"Ferramenta '{name}' não encontrada."}
    fn = tool.get("fn")
    if not fn:
        return {"ok": False, "result": None, "error": f"Ferramenta '{name}' não possui função associada."}

    try:
        result = fn(**(args or {}))
        record_action(name)
        return {"ok": True, "result": result, "error": None}
    except TypeError as e:
        # Erro comum: parâmetros faltando ou nomes errados
        return {"ok": False, "result": None, "error": f"Erro de parâmetros ao chamar '{name}': {e}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "result": None, "error": str(e)}

