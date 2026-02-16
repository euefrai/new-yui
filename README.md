# Yui — Assistente de código e analisador de projetos

Assistente de código autônoma com **chat web** (estilo WhatsApp/Instagram) e **análise de projetos** via CLI. Memória persistente, resposta contextual e geração de código em várias linguagens.

## Requisitos

- Python 3.11+

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para instalar todas as dependências (voz, automação, build): `pip install -r requirements-dev.txt`

## Chat web (local)

```bash
python web_server.py
```

Acesse: **http://127.0.0.1:5000**

Configure `OPENAI_API_KEY` no arquivo `.env` (copie de `.env.example`) para usar a IA.

## Login e chats por usuário (Supabase)

A interface principal usa **Supabase** para login e para separar chats por usuário (sidebar estilo ChatGPT, nome no rodapé).

1. Crie um projeto em [supabase.com](https://supabase.com).
2. No SQL Editor do Supabase, execute o conteúdo de **`supabase_schema.sql`** (cria as tabelas `chats` e `messages` e opcionalmente `users_profile`). Opcional: execute **`supabase_migration_messages_extra.sql`** para adicionar colunas `type`, `metadata` e `status` na tabela `messages` (replay de ferramentas, histórico estruturado).
3. No `.env` (ou nas variáveis de ambiente do Zeabur/Render), defina:
   - `SUPABASE_URL` = URL do projeto (ex.: `https://xxxx.supabase.co`)
   - `SUPABASE_ANON_KEY` = chave **anon** (pública) — usada só no **frontend** (login/Auth no navegador).
   - `SUPABASE_SERVICE_KEY` = chave **service_role** — usada só no **backend** (persistir chats, etc.). Nunca expor no frontend.
   Usar as duas evita: se colocar só service_role no frontend quebra segurança; se colocar só anon no backend algumas operações falham.
4. Reinicie o servidor e acesse a raiz da aplicação: tela de login → após entrar, sidebar com chats e área de mensagens.

Sem Supabase configurado, a rota `/` ainda carrega a interface, mas login e persistência de chats não funcionam (é necessário configurar as variáveis).

**Memória — uma fonte só:** se `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` estiverem definidos, a memória usa a nuvem (Supabase). Caso contrário, usa JSON local. Misturar os dois sem essa lógica gera conflito de “fonte de verdade” (ex.: “cadê minha conversa?”).

## Deploy no Zeabur

1. Faça push deste repositório para o GitHub.
2. Acesse [zeabur.com](https://zeabur.com) e crie uma conta (ou use "Sign in with GitHub").
3. **Add new service** → **Deploy your source code** → conecte o repositório.
4. O Zeabur detecta Python/Flask. O `Procfile` define o start com Gunicorn.
5. Em **Variables** adicione:
   - `OPENAI_API_KEY` = sua chave da OpenAI (obrigatório para o chat com IA).
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_KEY` = para login e chats por usuário (opcional).
6. Deploy automático ao fazer push no GitHub.

O Zeabur gera uma URL como `https://seu-projeto.zeabur.app`. Em cloud, a Yui usa modo LITE (menos RAM, sem ChromaDB).

## Deploy no Render

1. Faça push deste repositório para o GitHub.
2. Acesse [render.com](https://render.com) e crie uma conta (ou use “Sign in with GitHub”).
3. **New** → **Blueprint** e conecte o repositório **euefrai/new-yui** (ou o seu fork).
4. O `render.yaml` já define o serviço. Confirme:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn --bind 0.0.0.0:$PORT web_server:app`
5. Em **Environment** adicione:
   - `OPENAI_API_KEY` = sua chave da OpenAI (obrigatório para o chat com IA).
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_KEY` = para login e chats por usuário (opcional).
6. Clique em **Apply** e aguarde o deploy.

O Render vai gerar uma URL como `https://yui-xxxx.onrender.com`. Use essa URL no navegador para o chat. Em plano gratuito o serviço pode “dormir” após inatividade; a primeira requisição pode demorar alguns segundos.

## Uso via CLI

### Analisar um projeto

```bash
yui analyze <caminho_do_projeto>
```

Exemplos:

```bash
# Analisar o diretório atual
python cli.py analyze .

# Analisar outro projeto
python cli.py analyze ./meu-projeto

# Via módulo
python -m yui_ai analyze ./meu-projeto
```

### O que a análise faz

- **Escaneia** a estrutura de pastas e arquivos
- **Mapeia** arquivos Python e imports (AST)
- **Detecta** responsabilidades e padrões arquiteturais
- **Identifica** dependências circulares
- **Avalia** pontos fortes, fracos e riscos técnicos
- **Gera** relatório técnico no terminal (roadmap de melhorias)

Nenhum arquivo do projeto analisado é modificado.

## Fluxo do agente (chat web)

O backend **não** devolve a resposta bruta do modelo. Toda mensagem passa pelo **agent controller**:

1. **Context engine** monta histórico, memória vetorial, contexto do projeto e do chat.
2. O **modelo** pode responder em JSON: `{"mode":"answer","answer":"..."}` ou `{"mode":"tools","steps":[...]}` ou `{"usar_skill":"nome","dados":{...}}`.
3. Se for **tools**, o backend **executa as ferramentas** (analisar_arquivo, listar_arquivos, etc.), monta um texto legível e **só então** envia ao frontend.
4. Um **tool router** remove qualquer JSON residual antes de streamar; o usuário **nunca** vê JSON cru de ferramentas.

Ou seja: a Yui decide quando usar ferramenta, executa em silêncio e responde em texto. O frontend só recebe streaming de texto.

## Plugins como ferramentas automáticas

Ferramentas são registradas em **`core/tools_registry.py`**. Os **plugins** em `plugins/` são carregados automaticamente ao subir o servidor: cada módulo em `plugins/*.py` que chama `register_tool(name, fn, description, schema)` passa a expor essa ferramenta para o agente. Exemplo: `plugins/filesystem_plugin.py` registra `listar_arquivos` e `ler_arquivo_texto`. Para adicionar uma nova capacidade, crie um arquivo em `plugins/` e chame `register_tool` no nível do módulo; o agent controller já escolhe quando usar cada tool com base no prompt do modelo.

## Estrutura do analisador

```
yui_ai/
  analyzer/
    project_scanner.py   # Estrutura de pastas e listagem de .py
    dependency_mapper.py # Grafo de imports (AST), ciclos
    architecture_analyzer.py # Responsabilidades e camadas
    risk_detector.py     # Pontos fortes/fracos, riscos
    report_builder.py    # Orquestração e relatório final
cli.py                  # Entrypoint CLI (yui analyze)
```

## Desenvolvimento

```bash
# Rodar análise no próprio projeto Yui
python cli.py analyze .
```

## Estrutura do projeto

```
yui_ai/          # Core da assistente (memória, IA, analisador)
core/            # Engine web (agent, tools, event bus)
web/             # Rotas Flask (blueprints)
services/        # Camada de serviços (chat, IA)
static/          # Assets do chat (app.js, chat.js, style.css)
templates/       # HTML principal (index.html)
web_server.py    # App Flask — rode: python web_server.py
cli.py           # CLI — rode: python cli.py analyze . ou python cli.py map .
Procfile         # Deploy Zeabur (gunicorn)
render.yaml      # Configuração de deploy no Render
```

**Dois modos de uso:**
- **Chat web:** `python web_server.py` → http://127.0.0.1:5000
- **CLI (análise):** `python cli.py analyze <path>` ou `python cli.py map <path>`

A pasta `web/` contém rotas e assets legados; a interface principal usa `templates/` + `static/`.

## Testes

```bash
# Na raiz do projeto
python -m pytest tests/ -v
```

## Licença

Uso interno / projeto pessoal.
