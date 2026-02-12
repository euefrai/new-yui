# Performance — Otimizações para Zeabur / Tencent Cloud / VPS

## Implementado

### 1. Modo LITE em cloud (Tencent, VPS, etc.)
Para VPS com pouca RAM (ex.: Tencent Cloud), defina:
```bash
YUI_LITE_MODE=true
# ou
TENCENT_CLOUD=true
```
Desativa planner, vector_memory, auto_debug e goals — reduz RAM e CPU.

### 2. Lazy Loading do Workspace
- **Monaco Editor** e **árvore de arquivos** só carregam quando o usuário abre o Workspace (Ctrl+L).
- **Xterm**, **JSZip** e **FitAddon** carregam sob demanda ao abrir o Workspace.
- Reduz carga inicial em ~2–3 MB de scripts.

### 3. Debounce na Telemetria
- Polling de sistema (CPU, RAM, telemetria, cognitive) a cada **30 segundos**.
- Executa **apenas quando o chat está ativo** (appScreen visível).

### 4. Cache de telemetria
- CPU/RAM lidos a cada **20 segundos** (cache).
- Context kernel: listagem apenas **nível raiz** (iterdir), cache **30s**.

### 5. Cleanup Backend
- `POST /api/system/cleanup` remove:
  - `generated_projects/`
  - `_run_script.py` e `_run_script.js` no sandbox
- Configurar cron no Zeabur para chamar periodicamente (ex: a cada 6h).

### 6. Minificação
- `python scripts/minify_static.py` gera `*.min.js` e `*.min.css`.
- Definir `USE_MINIFIED_STATIC=true` no Zeabur.
- Adicionar no build: `python scripts/minify_static.py`

### 7. Modo de Economia
- Quando **RAM > 70%**, o body recebe a classe `economy-mode`.
- Desativa animações neon e sombras pesadas (CSS).
- Reduz processamento no navegador.

### 8. Limite de histórico (RAM)
- `get_messages(limit=50)` — query Supabase retorna só últimas 50 mensagens
- `load_history(limit=100)` — API retorna últimas 100
- context_engine: MAX_MENSAGENS_DB=50, MAX_MENSAGENS_HISTORICO=12

### 9. Plugins lazy load
- Plugins carregam na primeira invocação de tool (não no startup)
- Reduz RAM inicial em servidores 2GB

### 10. Preview só quando aba ativa
- `updateWorkspacePreview` retorna cedo se `document.hidden`
- `visibilitychange`: esvazia iframe ao trocar de aba
- Debounce 400ms em `workspacePreviewUpdate` (evita re-render a cada tecla)

### 11. Gunicorn enxuto
- `workers=1`, `threads=2` no Procfile (Zeabur/Heroku).
- Para 2GB: `WEB_CONCURRENCY=1` (evita duplicar memória).

### 12. Client-Side Processing
- **Highlight.js** formata código no navegador.
- Servidor atua como roteador de mensagens e storage.

## Deploy no Tencent Cloud (VPS)

Configure no seu servidor:
```bash
export YUI_LITE_MODE=true
# ou
export TENCENT_CLOUD=true
```
Recomendado para VPS com 2 vCPU e 4GB RAM ou menos.

## Deploy no Zeabur

```yaml
# Adicionar ao build
buildCommand: |
  pip install -r requirements.txt
  python scripts/minify_static.py

# Variáveis de ambiente
USE_MINIFIED_STATIC=true
```

## Cron de Cleanup (Zeabur)

Criar job que chame:
```bash
curl -X POST https://seu-app.zeabur.app/api/system/cleanup
```
