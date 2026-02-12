# ==========================================================
# YUI SKILL REGISTRY
# Registro dinâmico de habilidades — agents registram, router consulta.
#
# Router NÃO conhece agentes. Router consulta Registry.
# Registry decide quem sabe fazer o quê.
#
# Agent → registra habilidades
# Registry → guarda habilidades
# Router → consulta registry
# ==========================================================

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional


@dataclass
class Skill:
    """Uma skill registrada: nome, agente, tags."""
    name: str
    agent: str
    tags: List[str]
    skip_planner: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)


class SkillRegistry:
    """
    Registry de habilidades. Agents registram; Router consulta.

    register(name, agent, tags) — registra skill
    find(capability_type) — retorna Skill ou None (match por tag)
    list_skills() — retorna skills ativas para UI
    """

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._lock = Lock()

    def register(
        self,
        name: str,
        agent: str,
        tags: List[str],
        skip_planner: bool = False,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra uma skill. Sobrescreve se name já existe."""
        with self._lock:
            self._skills[name] = Skill(
                name=name,
                agent=agent,
                tags=list(tags),
                skip_planner=skip_planner,
                meta=meta or {},
            )

    def find(self, capability_type: str) -> Optional[Skill]:
        """
        Encontra skill que trata o capability_type (match por tag).
        Retorna a primeira match.
        """
        with self._lock:
            ct = (capability_type or "").lower().strip()
            for skill in self._skills.values():
                if ct in [t.lower() for t in skill.tags]:
                    return skill
        return None

    def find_agent(self, capability_type: str) -> Optional[str]:
        """Atalho: retorna agent ou None."""
        skill = self.find(capability_type)
        return skill.agent if skill else None

    def list_skills(self) -> List[Dict[str, Any]]:
        """Retorna skills ativas para UI (auto-descoberta)."""
        with self._lock:
            return [
                {
                    "name": s.name,
                    "agent": s.agent,
                    "tags": s.tags,
                    "skip_planner": s.skip_planner,
                }
                for s in self._skills.values()
            ]

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Retorna todas as skills para o Confidence Engine (ranking).
        Inclui meta (context, priority) para scoring.
        """
        with self._lock:
            return [
                {
                    "name": s.name,
                    "agent": s.agent,
                    "tags": s.tags,
                    "skip_planner": s.skip_planner,
                    "meta": s.meta or {},
                }
                for s in self._skills.values()
            ]


_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """Retorna o SkillRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        _bootstrap_defaults()
    return _registry


def _bootstrap_defaults() -> None:
    """Registra skills padrão da Yui."""
    r = _registry
    # Heathcliff — code, analysis
    r.register("code-edit", "heathcliff", ["code_generation", "code"], skip_planner=False)
    r.register("analysis", "heathcliff", ["analysis", "analisar"], skip_planner=True)
    # Yui — general, lightweight
    r.register("general", "yui", ["general", "lightweight", "chat"], skip_planner=True)
    # RAG — memory
    r.register("memory-search", "rag_engine", ["memory_query", "memory", "rag"], skip_planner=True)
    # Execution Graph — system
    r.register("live-preview", "execution_graph", ["system_action", "preview"], skip_planner=False)
    r.register("terminal-exec", "execution_graph", ["system_action", "terminal", "exec"], skip_planner=False)
    r.register("zip-builder", "execution_graph", ["system_action", "zip"], skip_planner=False)


def register_skill(
    name: str,
    agent: str,
    tags: List[str],
    skip_planner: bool = False,
) -> None:
    """Registra skill no registry global."""
    get_registry().register(name, agent, tags, skip_planner=skip_planner)


def find_skill(capability_type: str) -> Optional[Skill]:
    """Encontra skill que trata o capability_type."""
    return get_registry().find(capability_type)


def list_skills() -> List[Dict[str, Any]]:
    """Retorna skills ativas para UI."""
    return get_registry().list_skills()


def get_all_skills() -> List[Dict[str, Any]]:
    """Retorna todas as skills para o Confidence Engine."""
    return get_registry().get_all()
