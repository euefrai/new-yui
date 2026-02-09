# Memória e contexto na Yui

Este documento explica como funciona a **memória local de mensagens** e a **edição contextual de respostas** na Yui.

---

## Como funciona a memória

- A Yui guarda as **últimas 100 mensagens** da conversa (suas e da assistente).
- Tudo é salvo **apenas no seu computador**, no arquivo:
  - **Windows:** `%LOCALAPPDATA%\Yui\chat_memory.json`
- Nenhum conteúdo é enviado para servidores externos para memória; o arquivo é criado e lido localmente pelo próprio processo da Yui.

### O que é guardado em cada mensagem

Cada entrada na memória tem:

| Campo       | Descrição                                      |
|------------|--------------------------------------------------|
| `id`       | Identificador único (UUID) da mensagem           |
| `autor`    | `"usuario"` ou `"yui"`                            |
| `conteudo` | Texto completo da mensagem                        |
| `tipo`     | `"texto"`, `"codigo"`, `"arquivo"` ou `"relatorio"` |
| `timestamp`| Data/hora em formato ISO                         |
| `resumo`   | Resumo curto automático do conteúdo              |

A memória é usada para:

- **Responder com seta (reply):** ao clicar em "↩ Responder" numa mensagem da Yui, a próxima mensagem é enviada com referência àquela. O sistema busca o conteúdo original na memória e usa como contexto, sem precisar colar de novo.
- **Editar resposta anterior:** quando você pede "altera isso", "melhora o código", "ajusta a resposta", etc., a Yui usa a **última resposta dela** na memória como base e aplica seu pedido, devolvendo o que foi alterado e a nova versão.

---

## Como editar respostas anteriores

Você pode pedir alterações **sem reenviar** o código ou o texto. Exemplos:

- "Altera isso"
- "Muda aquilo"
- "Ajusta a resposta"
- "Melhora o código"
- "Refatora o que você mandou"
- "Corrige o que você mandou"

O fluxo é:

1. A Yui identifica a intenção de **editar resposta**.
2. Busca na memória a **última mensagem da Yui**.
3. Se existir, aplica seu pedido em cima desse conteúdo e responde com:
   - **🛠️ O QUE FOI ALTERADO** — lista objetiva das mudanças
   - **📄 NOVA VERSÃO** — conteúdo atualizado

Se **não houver** uma resposta anterior válida na memória (por exemplo, início da conversa ou memória vazia), a Yui responde:

> "Não encontrei uma resposta anterior para editar. Me diga qual parte você quer alterar."

Ela **nunca inventa** conteúdo; só edita o que realmente está na memória.

---

## Privacidade e limites

- **Privacidade:** os dados da memória ficam **somente no seu PC**, no caminho indicado acima. A Yui não envia esse arquivo para terceiros.
- **Limite:** são mantidas apenas as **últimas 100 mensagens**. As mais antigas são removidas quando o limite é ultrapassado.
- **Segurança:** o sistema só altera ou usa mensagens que existem na memória; não há edição de mensagens inexistentes.

---

## Resumo rápido

| Recurso            | Descrição |
|--------------------|-----------|
| Memória            | Até 100 mensagens, em `%LOCALAPPDATA%\Yui\chat_memory.json` |
| Reply (↩ Responder)| Botão em mensagens da Yui; próxima mensagem vai com contexto daquela |
| Editar resposta    | Frases como "altera isso" ou "melhora o código" editam a última resposta da Yui |
| Privacidade        | Tudo local; sem envio da memória para serviços externos |
