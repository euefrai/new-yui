# ==========================================================
# YUI ACTION PLANNER — Mini Arquiteto Interno
#
# Não executa nada. Só responde: QUAL sequência de tarefas precisa acontecer.
#
# Fluxo: Intent Parser → Planner → Task Engine → Streaming UI
#
# Evita: IA tenta fazer tudo de uma vez → CPU sobe, RAM sofre, SIGKILL
# Permite: Yui pensa antes de agir, executa em etapas pequenas
# ==========================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlannedStep:
    """Uma etapa do plano: task (tool ou ação), label para UI, args placeholder."""
    task: str
    label: str
    tool: Optional[str] = None  # nome da tool no registry
    args_key: Optional[str] = None  # chaves esperadas (ex: root_dir,files)
    meta: Dict[str, Any] = field(default_factory=dict)


# Mapeamento task → emoji + texto para UI
TASK_LABELS: Dict[str, str] = {
    "planejando": "⚙️ Planejando...",
    "criar_estrutura": "📁 Criando estrutura...",
    "criar_projeto_arquivos": "📁 Criando arquivos...",
    "criar_zip_projeto": "📦 Gerando ZIP...",
    "analisar_projeto": "🔍 Analisando projeto...",
    "analisar_arquivo": "🔎 Analisando código...",
    "observar_ambiente": "👁️ Observando ambiente...",
    "consultar_indice_projeto": "📋 Consultando índice...",
    "validar": "🧪 Validando código...",
    "fs_create_file": "✏️ Editando arquivo...",
    "fs_create_folder": "📂 Criando pasta...",
    "fs_delete_file": "🗑️ Removendo...",
    "buscar_web": "🌐 Buscando na web...",
    "responder": "💬 Respondendo...",
}


class Planner:
    """
    Mini arquiteto interno. Não executa nada.
    Retorna sequência de tarefas que precisam acontecer.
    """

    def __init__(self):
        self._templates: Dict[str, List[PlannedStep]] = {}
        self._bootstrap()

    def _bootstrap(self) -> None:
        """Registra templates de intenção → sequência de steps."""
        self._templates = {
            "criar_projeto": [
                PlannedStep(task="criar_estrutura", label=TASK_LABELS["criar_estrutura"], tool=None),
                PlannedStep(task="criar_projeto_arquivos", label=TASK_LABELS["criar_projeto_arquivos"], tool="criar_projeto_arquivos", args_key="root_dir,files"),
                PlannedStep(task="criar_zip_projeto", label=TASK_LABELS["criar_zip_projeto"], tool="criar_zip_projeto", args_key="root_dir,zip_name"),
                PlannedStep(task="validar", label=TASK_LABELS["validar"], tool=None),
            ],
            "criar_projeto_web": [
                PlannedStep(task="criar_estrutura", label=TASK_LABELS["criar_estrutura"], tool=None),
                PlannedStep(task="criar_projeto_arquivos", label=TASK_LABELS["criar_projeto_arquivos"], tool="criar_projeto_arquivos", args_key="root_dir,files"),
                PlannedStep(task="criar_zip_projeto", label=TASK_LABELS["criar_zip_projeto"], tool="criar_zip_projeto", args_key="root_dir,zip_name"),
                PlannedStep(task="validar", label=TASK_LABELS["validar"], tool=None),
            ],
            "analisar_codigo": [
                PlannedStep(task="analisar_arquivo", label=TASK_LABELS["analisar_arquivo"], tool="analisar_arquivo", args_key="filename,content"),
            ],
            "analisar_projeto": [
                PlannedStep(task="analisar_projeto", label=TASK_LABELS["analisar_projeto"], tool="analisar_projeto", args_key="raiz"),
            ],
            "refatorar_codigo": [
                PlannedStep(task="ler_arquivos", label="📖 Lendo arquivos...", tool=None),
                PlannedStep(task="analisar_arquivo", label=TASK_LABELS["analisar_arquivo"], tool="analisar_arquivo", args_key="filename,content"),
                PlannedStep(task="aplicar_patch", label="✏️ Aplicando alterações...", tool="fs_create_file", args_key="path,content"),
            ],
            "observar_ambiente": [
                PlannedStep(task="observar_ambiente", label=TASK_LABELS["observar_ambiente"], tool="observar_ambiente", args_key="raiz"),
            ],
            "consultar_indice": [
                PlannedStep(task="consultar_indice_projeto", label=TASK_LABELS["consultar_indice_projeto"], tool="consultar_indice_projeto", args_key="raiz"),
            ],
        }

    def inferir_intencao(self, mensagem: str) -> str:
        """Infere a intenção principal a partir da mensagem (heurístico)."""
        t = (mensagem or "").lower().strip()
        # Criar projeto
        if any(x in t for x in ("criar", "cria", "gerar", "fazer")):
            if any(x in t for x in ("calculadora", "login", "sistema", "api", "projeto", "site", "web", "html")):
                return "criar_projeto_web" if "web" in t or "site" in t or "html" in t else "criar_projeto"
        # Refatorar
        if any(x in t for x in ("refatorar", "refatora", "melhorar", "corrigir", "bug", "erro")):
            if "código" in t or "codigo" in t or "arquivo" in t:
                return "refatorar_codigo"
        # Analisar
        if "analis" in t or "analise" in t:
            if "arquivo" in t or "código" in t or "codigo" in t:
                return "analisar_codigo"
            if "projeto" in t:
                return "analisar_projeto"
        # Observar
        if "observar" in t or "visão" in t or "visao" in t or "estrutura" in t:
            return "observar_ambiente"
        # Consultar índice
        if "consultar" in t or "índice" in t or "indice" in t:
            return "consultar_indice"
        return "chat"

    def planejar(self, intencao: str, mensagem: str = "") -> List[Dict[str, Any]]:
        """
        Retorna sequência de tarefas para a intenção.
        Não executa nada. Formato: [{"task": str, "label": str, "tool": str?}, ...]
        """
        if intencao == "chat":
            return [{"task": "responder", "label": TASK_LABELS["responder"], "tool": None}]
        steps = self._templates.get(intencao, [])
        return [
            {"task": s.task, "label": s.label, "tool": s.tool, "args_key": s.args_key}
            for s in steps
        ]

    def get_label_for_tool(self, tool_name: str) -> str:
        """Retorna label para UI dado o nome da tool."""
        return TASK_LABELS.get(tool_name, f"🔧 Executando {tool_name}...")

    def get_label_planejando(self) -> str:
        """Label para fase de planejamento."""
        return TASK_LABELS["planejando"]


# --- Singleton ---
_planner: Optional[Planner] = None


def get_action_planner() -> Planner:
    """Retorna o Action Planner singleton."""
    global _planner
    if _planner is None:
        _planner = Planner()
    return _planner
