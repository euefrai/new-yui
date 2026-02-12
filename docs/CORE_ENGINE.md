# Core Engine — Arquitetura da Yui

A Yui não é chatbot nem IDE. É uma **mini DevOS** baseada em IA:
**Workspace + Runtime + Memória + Agente**.

## Arquitetura

```
[Usuário] → Agent Controller
                ↓
           [model="auto" → Arbitration Engine decide_leader]
                ↓
           Action Engine → Context Kernel → Persona (Yui/Heathcliff/Hybrid)
                ↓                ↓                ↓
           [editor]        [arquivos]        [tools]
           [terminal]      [erros]          [RAG]
           [analyzer]      [chat]           [executor]
           [RAG]           [workspace]
```

## Módulos

### 1. Action Engine (`core/engine/action_router.py`)

O coração do orquestrador. Decide **quando**:
- abrir editor
- executar código
- usar terminal
- chamar analyzer
- fazer RAG

```python
from core.engine import route_action

intent = route_action("executar o main.py", last_tool="analisar_projeto")
# intent.action = "execute_code"
# intent.tool_hint = "execute_sandbox"
```

### 2. Arbitration Engine (`core/arbitration_engine.py`)

**Decision Layer** — decide qual persona lidera (Yui, Heathcliff ou Hybrid).

- model="auto" → heurística decide: refatorar/backend/arquitetura → Heathcliff; ui/texto/fluxo → Yui; else → Hybrid
- model="yui" | "heathcliff" → preferência manual
- Reduz inconsistência; Planner e Self-Critic ficam mais previsíveis

```python
from core.arbitration_engine import decide_leader

arb = decide_leader("refatorar o backend", has_console_errors=True)
# arb.leader = "heathcliff"
```

### 3. Context Kernel (`core/engine/context_kernel.py`)

Unifica o contexto em tempo real:
- arquivos ativos
- erros do console
- histórico do chat
- estado do workspace

```python
from core.engine import get_context_snapshot, snapshot_to_prompt

snapshot = get_context_snapshot()
prompt_text = snapshot_to_prompt(snapshot)
```

### 4. Execution Graph Engine (`core/execution_graph.py`)

**Orquestrador de fluxo** — toda ação vira um nó observável.

- Input → Planner cria mini-fluxo → Nodes executam → Observer acompanha → Critic valida
- Permite: pausar, reexecutar nó, progresso visual, custo por etapa
- Emite eventos: `execution_node_start`, `execution_node_done`, `execution_node_failed`

```python
from core.execution_graph import ExecutionGraph, Node, graph_from_planner_steps

# Exemplo: "Cria API e gera ZIP"
g = ExecutionGraph(intention="criar_api_zip")
g.add_step("Parse Intent", lambda ctx: ctx)
g.add_step("Generate Files", lambda ctx: {"files": [...]})
# Zip Builder usa Task Scheduler (background); link [DOWNLOAD] aparece logo
g.add_step("Zip Builder", lambda ctx: "/download/projeto.zip")
g.add_step("Download Link", lambda ctx: ctx.get("_result_Zip Builder"))

result = g.run(ctx={"user_message": "cria API de login"})
status = g.to_ui_status()  # [{"name": "Parse Intent", "status": "done", "symbol": "✓"}, ...]
```

### 5. System State Engine (`core/system_state.py`)

**Cérebro de estado** — consistência operacional.

- `mode`, `workspace_open`, `executing_graph`, `terminal_sessions_alive`
- `should_enable_editor_features()`: só quando workspace aberto
- `should_activate_observer()`: só quando Execution Graph rodando

```python
from core.system_state import get_state, should_enable_editor_features

if should_enable_editor_features():
    enable_editor_features()
```

### 6. Resource Governor (`core/resource_governor.py`)

**Controle inteligente de recursos** — decide "posso executar isso agora?".

- `allow_preview(ram)` — preview só se RAM < 75%
- `allow_heavy_agent(cpu, ram)` — agent pesado só se CPU < 85%, RAM < 80%
- `allow_planner(cpu)` — planner só se CPU < 90%
- `allow_watchers(ram)` — watchers só se RAM < 70%

```python
from core.resource_governor import get_governor

if get_governor().allow_preview().allow:
    start_live_preview()
```

### 7. Event Bus (`core/event_bus.py`)

**Sistema Nervoso** — nenhum módulo chama outro direto. Tudo vira eventos.

- `on(event, fn)` / `subscribe(event, fn)`
- `emit(event, **kwargs)`
- Eventos principais:
  - `workspace_toggled` (open: bool)
  - `file_changed` (path, action)
  - `agent_requested` (model, user_message)
  - `preview_started`, `memory_updated`
  - `memory_update_requested` (root?) → scheduler adiciona indexar
  - `task_queued`, `task_done`, `task_failed`
  - `zip_ready` (download_url) — ZIP gerado em background

```python
from core.event_bus import emit, on

emit("workspace_toggled", open=True)
on("file_changed", lambda path, action: invalidate_cache(path))
```

### 8. Event Wiring (`core/event_wiring.py`)

Conecta eventos aos módulos no startup. Chamado por `web_server.py`.

- `workspace_toggled` → `system_state.set_workspace_open()`
- `memory_update_requested` → `scheduler.add(indexar_projeto)`

### 9. Task Scheduler (`core/task_scheduler.py`)

**Ações assíncronas** — separa imediato vs fila vs background.

- `add(fn, data)` → entra na fila, executa em background
- `add_now(fn, data)` → executa em thread separada (não bloqueia)
- Eventos: `task_queued`, `task_done`, `task_failed`
- **Usos**: indexação RAG, geração de ZIP (não bloqueia o chat)

```python
from core.task_scheduler import get_scheduler

get_scheduler().add(lambda d: indexar_projeto(d), data=raiz)
```

### 10. Pending Downloads (`core/pending_downloads.py`)

URLs de arquivos gerados em background (ex: ZIP). Frontend faz poll para saber quando está pronto.

- `add_ready(url)` — registra download pronto
- `get_recent(since?)` — retorna URLs prontas (TTL 5 min)

### 11. Skill Registry (`core/skills/registry.py`)

**Registro dinâmico de habilidades** — Router NÃO conhece agentes. Router consulta Registry.

- `register(name, agent, tags, skip_planner?)` — registra skill
- `find(capability_type)` — retorna Skill ou None (match por tag)
- `list_skills()` — skills ativas para UI (auto-descoberta)

Bootstrap padrão: code-edit, analysis, general, memory-search, live-preview, terminal-exec, zip-builder.

```python
from core.skills.registry import find_skill, register_skill, list_skills

skill = find_skill("code_generation")  # → Skill(agent="heathcliff", ...)
register_skill("design-mockup", "design_agent", ["design", "ui"])  # plugin novo
```

### 12. Capability Router (`core/capability_router.py`)

**Roteador de habilidades** — decide qual módulo resolve antes do planner.

- `route(user_message, intention?, action?, tool_hint?)` → RouteDecision
- **Consulta Skill Registry** para obter target e skip_planner (sem if/else de agentes)
- Fallback: mapping padrão quando registry não tem match

Integrado no agent_controller antes do planner. Registra routing no Observability.

```python
from core.capability_router import route, get_routing_display

dec = route(user_message, intention="analisar_projeto")
# dec.target = "heathcliff", dec.skip_planner = True (via registry.find)
```

### 13. Observability Layer (`core/observability.py`)

**Consciência interna** — rastreamento de ações e timeline.

- `trace(name, meta?)` — context manager para medir execução
- `record_activity(kind, label, detail)` — registra para System Activity
- `get_timeline()` — spans com duração (ms)
- `get_system_activity()` — atividade recente (graph, task, governor, event)
- `wire_observability()` — conecta Event Bus, Scheduler, Governor

Integrado em: Execution Graph (Trace por nó), Task Scheduler (Trace por task), Resource Governor (bloqueios).

### 14. Sandbox Executor (`core/sandbox_executor/runner.py`)

Execução isolada — anti-SIGKILL:
- subprocess isolado
- timeout configurável
- limite de RAM (Unix)
- não roda no worker principal

```python
from core.sandbox_executor import run_code

result = run_code("print(1+1)", lang="python", timeout=30)
```

### 15. Plugin Loader (`core/plugins_loader.py`)

- **scan**: descobre plugins em `plugins/`
- **register**: registra tools no `tools_registry`
- **inject**: disponibiliza ao engine no startup

```python
from core.plugins_loader import inject_into_engine

tools = inject_into_engine()  # lista de tools disponíveis
```

## Integração

- **API**: `/api/sandbox/execute` usa `run_code` do sandbox_executor
- **Startup**: `web_server.py` chama `wire_events()` (event_wiring) e `inject_into_engine()`
- **Agent**: `action_router` e `context_kernel` podem ser usados no `agent_controller` para enriquecer contexto e decisões

## Fluxo Capability Router + Skill Registry

```
user_message
    → Action Engine (route_action)
    → Capability Router (route) — heurísticas → capability_type
    → Skill Registry (find) — obtém target e skip_planner
    → skip_planner? → max_steps=2
    → Planner (se habilitado)
    → IA (Heathcliff/Yui/RAG/Execution Graph)
```

Router não conhece agentes. Registry decide quem sabe fazer o quê. Qualquer módulo vira plugin.

Routing exibido em System Activity: "→ Heathcliff (Engineering) (skip planner)"

## API System (`/api/system/*`)

| Endpoint | Descrição |
|----------|-----------|
| `GET /health` | CPU, RAM, modo (normal/fast/critical) |
| `GET /telemetry` | Custo acumulado, energia |
| `GET /governor` | allow_preview, allow_planner, allow_heavy_agent |
| `GET /scheduler` | queue_size da fila de tarefas |
| `GET /observability` | timeline (spans com ms) + activity (System Activity) |
| `GET /skills` | Skill Registry — skills ativas (auto-descoberta) |
| `GET /pending_downloads` | URLs de downloads prontos (?since=timestamp) |
| `GET /state` | mode, workspace_open, executing_graph |
| `GET /execution` | Nós do Execution Graph para UI |
| `POST /events` | Frontend emite: workspace_toggled, file_changed, preview_started |

## Fluxo assíncrono (Scheduler)

```
evento                    →  listener              →  ação
────────────────────────────────────────────────────────────────
memory_update_requested   →  event_wiring          →  scheduler.add(indexar)
criar_projeto_arquivos    →  agent_controller      →  run_tool(criar_zip, background=True)
task_done (zip)           →  _run_zip interno      →  add_ready(url), emit(zip_ready)
frontend [DOWNLOAD]       →  poll pending_downloads→  mostra "✓ Baixar Projeto"
```

**Antes**: Yui pensa → trava → responde  
**Depois**: Yui responde → continua trabalhando em silêncio

## Próximos passos

1. **Frontend**: enviar `active_files` e `console_errors` no chat para o Context Kernel
2. **Agent**: usar `route_action` para sugerir tool_hint ao planner
3. **Plugins**: adicionar mais plugins em `plugins/`; suportam `--list` e `invoke`
