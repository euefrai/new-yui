# ==========================================================
# YUI REFLECTION ENGINE (v2)
# Depois de executar: resultado → reflexão → ajustar próximo passo.
# Não é consciência; é loop lógico sofisticado.
# ==========================================================

from typing import Any, Dict, List, Optional

from core.planner import PlanStep


def refletir(
    resultado: Dict[str, Any],
    step: Optional[PlanStep] = None,
    plan_restante: Optional[List[PlanStep]] = None,
) -> Dict[str, Any]:
    """
    Analisa o resultado e decide se deve ajustar o plano.
    Retorna {ajustar: bool, motivo: str, novo_plano: list ou None}.
    """
    if not resultado:
        return {"ajustar": False, "motivo": "", "novo_plano": None}

    erro = resultado.get("error") or ""
    ok = resultado.get("ok", True)

    if not ok and erro:
        # Falhou: sugerir ajuste
        if "zip" in (erro or "").lower() or "criar_zip" in (str(step.tool) if step else "").lower():
            return {
                "ajustar": True,
                "motivo": "Falha ao compactar; continuar sem zip.",
                "novo_plano": [s for s in (plan_restante or []) if s.tool != "criar_zip_projeto"],
            }
        if "arquivo" in erro.lower() or "permission" in erro.lower():
            return {
                "ajustar": True,
                "motivo": "Erro de arquivo/permissão; tentar alternativa.",
                "novo_plano": plan_restante,
            }
        return {
            "ajustar": True,
            "motivo": f"Erro: {erro[:100]}",
            "novo_plano": plan_restante,
        }

    return {"ajustar": False, "motivo": "", "novo_plano": None}


def refletir_resultados(resultados: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reflexão sobre lista de resultados (último step)."""
    if not resultados:
        return {"ajustar": False, "motivo": "", "novo_plano": None}
    return refletir(resultados[-1])
