# Core Engine — Arquitetura da Yui

A Yui não é chatbot nem IDE. É uma **mini DevOS** baseada em IA:
**Workspace + Runtime + Memória + Agente**.

## Arquitetura

```
[Usuário] → Action Engine → Context Kernel → Agent Controller
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

### 2. Context Kernel (`core/engine/context_kernel.py`)

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

### 3. Sandbox Executor (`core/sandbox_executor/runner.py`)

Execução isolada — anti-SIGKILL:
- subprocess isolado
- timeout configurável
- limite de RAM (Unix)
- não roda no worker principal

```python
from core.sandbox_executor import run_code

result = run_code("print(1+1)", lang="python", timeout=30)
```

### 4. Plugin Loader (`core/plugins_loader.py`)

- **scan**: descobre plugins em `plugins/`
- **register**: registra tools no `tools_registry`
- **inject**: disponibiliza ao engine no startup

```python
from core.plugins_loader import inject_into_engine

tools = inject_into_engine()  # lista de tools disponíveis
```

## Integração

- **API**: `/api/sandbox/execute` usa `run_code` do sandbox_executor
- **Startup**: `web_server.py` chama `inject_into_engine()`    
- **Agent**: `action_router` e `context_kernel` podem ser usados no `agent_controller` para enriquecer contexto e decisões

## Próximos passos

1. **Frontend**: enviar `active_files` e `console_errors` no chat para o Context Kernel
2. **Agent**: usar `route_action` para sugerir tool_hint ao planner
3. **Plugins**: adicionar mais plugins em `plugins/`; suportam `--list` e `invoke`
