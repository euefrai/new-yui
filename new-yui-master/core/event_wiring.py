# ==========================================================
# YUI EVENT WIRING
# Conecta eventos aos módulos (state, governor, scheduler).
# Cada parte independente — sem fios cruzados.
# ==========================================================

from core.event_bus import on


def wire_events() -> None:
    """
    Registra listeners. Chamado no startup do web_server.
    """
    # workspace_toggled → system_state
    def _on_workspace_toggled(open: bool = False, **kwargs):
        try:
            from core.system_state import set_workspace_open
            set_workspace_open(bool(open))
        except Exception:
            pass

    on("workspace_toggled", _on_workspace_toggled)

    # memory_update_requested → scheduler (indexar em background)
    def _on_memory_update_requested(root: str = "", **kwargs):
        try:
            from core.task_scheduler import get_scheduler
            from config import settings

            def _indexar(data):
                try:
                    from backend.ai.vector_memory import indexar_projeto
                    raiz = data or str(settings.BASE_DIR)
                    qtd = indexar_projeto(raiz)
                    print(f"🧠 Memória do projeto: {qtd} blocos indexados (yui_vector_db).")
                    return qtd
                except Exception as e:
                    print(f"⚠️ Indexação da memória vetorial ignorada: {e}")
                    return 0

            get_scheduler().add(_indexar, data=root or str(settings.BASE_DIR))
        except Exception:
            pass

    on("memory_update_requested", _on_memory_update_requested)

    # task_finished → Reflection Loop (avaliar contexto e armazenar estado_reflexao)
    def _on_task_finished(
        task_id: str = "",
        task_type: str = "",
        duration: float = 0,
        success: bool = True,
        error: str = "",
        meta: dict = None,
        **kwargs,
    ):
        try:
            from core.execution_guard import get_guard
            from core.reflection_loop import avaliar_e_armazenar
            d = get_guard().pode_executar()
            contexto = {
                "task": task_type or "unknown",
                "tempo_execucao": duration,
                "memoria_usada": d.ram_used_mb,
                "sucesso": success,
            }
            avaliar_e_armazenar(contexto)
        except Exception:
            pass

    on("task_finished", _on_task_finished)
