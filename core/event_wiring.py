# ==========================================================
# YUI EVENT WIRING
# Conecta eventos aos módulos (state, governor).
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
