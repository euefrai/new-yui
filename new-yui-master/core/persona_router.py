# ==========================================================
# YUI PERSONA ROUTER — Cérebro que decide quem age
#
# Intent → Context → Persona Router → Planner
#
# Não é "uma IA com duas skins". É duas inteligências cooperando:
# - Yui: criativo, UX, suporte, respostas amplas
# - Heathcliff: engenharia, código, respostas técnicas e concisas
#
# Integra com Reflection Loop: "RAM alta → Heathcliff assume" (mais curto)
# ==========================================================

from dataclasses import dataclass
from typing import Any, Dict, Optional


# Intents que demandam Heathcliff (engenharia)
_HEATHCLIFF_INTENTS = frozenset({
    "refatorar_codigo", "analisar_codigo", "analisar_projeto",
    "criar_projeto", "criar_projeto_web", "observar_ambiente", "consultar_indice",
    "editar_arquivo", "editar_codigo",
})
# Intents que demandam Yui (criativo, UX)
_YUI_INTENTS = frozenset({
    "chat",
})


@dataclass
class PersonaDecision:
    """Resultado da decisão: persona + motivo."""
    persona: str  # "yui" | "heathcliff"
    reason: str


class PersonaRouter:
    """
    Decide qual persona deve agir com base em intent e contexto.
    Lógica determinística — nada místico.
    """

    def decidir(
        self,
        intent: str,
        context: Dict[str, Any],
        user_preference: Optional[str] = None,
    ) -> PersonaDecision:
        """
        Decide persona ativa.

        Args:
            intent: intenção inferida (ex: "criar_projeto", "chat", "refatorar_codigo")
            context: estado operacional (modo, workspace_open, estado_reflexao, etc.)
            user_preference: preferência explícita do usuário ("yui" | "heathcliff" | None)

        Returns:
            PersonaDecision com persona e reason.
        """
        context = context or {}
        intent = (intent or "chat").strip().lower()

        # 1) Preferência explícita do usuário
        if user_preference in ("yui", "heathcliff"):
            return PersonaDecision(
                persona=user_preference,
                reason=f"Preferência do usuário: {user_preference}.",
            )

        # 2) Reflection Loop: modo economia → Heathcliff (respostas mais curtas, menos RAM)
        estado_reflexao = context.get("estado_reflexao") or ""
        try:
            from core.reflection_loop import get_estado_reflexao
            estado_reflexao = estado_reflexao or get_estado_reflexao()
        except Exception:
            pass
        if estado_reflexao == "modo_economia":
            return PersonaDecision(
                persona="heathcliff",
                reason="Servidor em modo economia (RAM alta); Heathcliff responde mais conciso.",
            )

        # 3) Workspace aberto → engenharia (código, arquivos)
        modo = context.get("modo") or ""
        workspace_open = context.get("workspace_open")
        if (modo == "workspace" or workspace_open is True) and intent in _HEATHCLIFF_INTENTS:
            return PersonaDecision(
                persona="heathcliff",
                reason="Workspace aberto + tarefa de engenharia.",
            )
        if modo == "workspace" and intent == "chat":
            # Chat em workspace pode ser dúvida técnica
            return PersonaDecision(
                persona="heathcliff",
                reason="Workspace aberto; Heathcliff prioriza.",
            )

        # 4) Intent explícita
        if intent in _HEATHCLIFF_INTENTS:
            return PersonaDecision(
                persona="heathcliff",
                reason=f"Intent de engenharia: {intent}.",
            )
        if intent in _YUI_INTENTS:
            return PersonaDecision(
                persona="yui",
                reason=f"Intent de conversa/suporte: {intent}.",
            )

        # 5) Fallback: Yui (mais amigável para ambíguos)
        return PersonaDecision(
            persona="yui",
            reason=f"Intent ambígua ({intent}); padrão Yui.",
        )


# --- Singleton ---
_router: Optional[PersonaRouter] = None


def get_persona_router() -> PersonaRouter:
    """Retorna o PersonaRouter singleton."""
    global _router
    if _router is None:
        _router = PersonaRouter()
    return _router


def decidir_persona(
    intent: str,
    context: Optional[Dict[str, Any]] = None,
    user_preference: Optional[str] = None,
) -> PersonaDecision:
    """Atalho: decide persona e retorna decisão."""
    return get_persona_router().decidir(intent, context or {}, user_preference)
