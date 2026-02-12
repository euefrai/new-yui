# Performance — Otimizações para Zeabur

## Implementado

### 1. Lazy Loading do Workspace
- **Monaco Editor** e **árvore de arquivos** só carregam quando o usuário abre o Workspace (Ctrl+L).
- **Xterm**, **JSZip** e **FitAddon** carregam sob demanda ao abrir o Workspace.
- Reduz carga inicial em ~2–3 MB de scripts.

### 2. Debounce na Telemetria
- Polling de sistema (CPU, RAM, telemetria, cognitive) a cada **10 segundos**.
- Executa **apenas quando o chat está ativo** (appScreen visível).

### 3. Cleanup Backend
- `POST /api/system/cleanup` remove:
  - `generated_projects/`
  - `_run_script.py` e `_run_script.js` no sandbox
- Configurar cron no Zeabur para chamar periodicamente (ex: a cada 6h).

### 4. Minificação
- `python scripts/minify_static.py` gera `*.min.js` e `*.min.css`.
- Definir `USE_MINIFIED_STATIC=true` no Zeabur.
- Adicionar no build: `python scripts/minify_static.py`

### 5. Modo de Economia
- Quando **RAM > 70%**, o body recebe a classe `economy-mode`.
- Desativa animações neon e sombras pesadas (CSS).
- Reduz processamento no navegador.

### 6. Client-Side Processing
- **Highlight.js** formata código no navegador.
- **Preview** (iframe) no Workspace é 100% client-side.
- Servidor atua como roteador de mensagens e storage.

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
