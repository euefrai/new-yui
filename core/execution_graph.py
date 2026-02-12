# ==========================================================
# YUI EXECUTION GRAPH ENGINE
# Camada onde toda ação vira um nó dentro de um fluxo.
#
# Conecta Planner → Observer → Self-Critic em um fluxo visível.
# Permite: pausar, reexecutar nó, progresso visual, custo por etapa.
# ==========================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    from core.event_bus import emit
except ImportError:
    emit = lambda e, *a, **k: None


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Node:
    """Nó do grafo: nome, ação e estado."""
    name: str
    action: Callable[[Dict[str, Any]], Any]
    status: NodeStatus = field(default=NodeStatus.PENDING)
    result: Any = None
    error: Optional[str] = None

    def run(self, ctx: Dict[str, Any]) -> Any:
        """Executa a ação e atualiza status."""
        self.status = NodeStatus.RUNNING
        emit("execution_node_start", node_name=self.name, ctx=ctx)
        try:
            from core.observability import trace
            with trace(self.name, meta={"intention": ctx.get("intention", "")}):
                self.result = self.action(ctx)
            self.status = NodeStatus.DONE
            self.error = None
            emit("execution_node_done", node_name=self.name, result=self.result, ctx=ctx)
            return self.result
        except Exception as e:
            self.status = NodeStatus.FAILED
            self.error = str(e)
            emit("execution_node_failed", node_name=self.name, error=str(e), ctx=ctx)
            raise


class ExecutionGraph:
    """
    Grafo de execução: sequência de nós observáveis.

    Fluxo: Input → Planner cria mini-fluxo → nodes executam → Observer acompanha → Critic valida.
    """

    def __init__(self, intention: str = ""):
        self.intention = intention
        self.nodes: List[Node] = []
        self._ctx: Dict[str, Any] = {}

    def add(self, node: Node) -> "ExecutionGraph":
        """Adiciona um nó ao grafo."""
        self.nodes.append(node)
        return self

    def add_step(self, name: str, action: Callable[[Dict[str, Any]], Any]) -> "ExecutionGraph":
        """Atalho para add(Node(name, action))."""
        return self.add(Node(name=name, action=action))

    def run(self, ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa todos os nós em sequência.
        ctx: contexto compartilhado entre nós (pode ser mutado).
        Consulta Resource Governor antes de executar.
        """
        try:
            from core.resource_governor import allow_execution_graph
            dec = allow_execution_graph()
            if not dec.allow:
                raise RuntimeError(f"Resource Governor bloqueou: {dec.reason}")
        except ImportError:
            pass
        try:
            from core.system_state import set_executing_graph
            set_executing_graph(True)
        except Exception:
            pass
        self._ctx = dict(ctx or {})
        results = []

        try:
            for node in self.nodes:
                try:
                    out = node.run(self._ctx)
                    results.append({"node": node.name, "status": node.status.value, "result": out})
                    self._ctx[f"_result_{node.name}"] = out
                except Exception:
                    results.append({"node": node.name, "status": node.status.value, "error": node.error})
                    emit("execution_graph_failed", graph=self, node=node)
                    raise

            emit("execution_graph_done", graph=self, results=results)
            return {"results": results, "ctx": self._ctx}
        finally:
            try:
                from core.system_state import set_executing_graph
                set_executing_graph(False)
            except Exception:
                pass

    def to_ui_status(self) -> List[Dict[str, str]]:
        """
        Retorna status para UI (progresso visual).

        Ex: [{"name": "Planner", "status": "done"}, {"name": "Generate Files", "status": "running"}, ...]
        Símbolos: ✓ done, ⏳ running, ○ pending
        """
        symbols = {
            NodeStatus.DONE: "✓",
            NodeStatus.RUNNING: "⏳",
            NodeStatus.FAILED: "✗",
            NodeStatus.PENDING: "○",
        }
        return [
            {"name": n.name, "status": n.status.value, "symbol": symbols.get(n.status, "○")}
            for n in self.nodes
        ]

    def get_context(self) -> Dict[str, Any]:
        """Retorna o contexto atual (após run parcial ou completo)."""
        return dict(self._ctx)


# ==========================================================
# Helpers para construir grafos comuns
# ==========================================================

def graph_from_planner_steps(
    steps: List[str],
    step_actions: Dict[str, Callable[[Dict[str, Any]], Any]],
) -> ExecutionGraph:
    """
    Cria um ExecutionGraph a partir de um plano (lista de nomes de etapas).
    step_actions: mapeia nome da etapa → função(ctx) -> result.
    """
    g = ExecutionGraph(intention="planner_flow")
    for step in steps:
        action = step_actions.get(step, lambda ctx: None)
        g.add_step(step, action)
    return g
