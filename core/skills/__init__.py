# ==========================================================
# YUI SKILL REGISTRY
# Registro dinâmico de habilidades — agents registram, router consulta.
# ==========================================================

from core.skills.registry import SkillRegistry, get_registry, register_skill, find_skill, list_skills, get_all_skills

__all__ = [
    "SkillRegistry",
    "get_registry",
    "register_skill",
    "find_skill",
    "list_skills",
    "get_all_skills",
]
