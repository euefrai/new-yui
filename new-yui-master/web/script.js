(function () {
  "use strict";

  const chat = document.getElementById("chat");
  const fileInput = document.getElementById("fileInput");
  const msgInput = document.getElementById("msgInput");
  const sendBtn = document.getElementById("sendBtn");
  const replyPreview = document.getElementById("replyPreview");
  const replyPreviewText = document.getElementById("replyPreviewText");
  const replyPreviewCancel = document.getElementById("replyPreviewCancel");

  // Se a página for aberta por file://, as requisições vão para o servidor local
  var API_BASE = "";
  if (window.location.protocol === "file:") {
    API_BASE = "http://127.0.0.1:5000";
  }

  let replyToId = null;
  let replyToSnippet = "";
  var apiKeyMissingShown = false;

  var apiKeyBanner = document.getElementById("apiKeyBanner");
  var apiKeyBannerClose = document.getElementById("apiKeyBannerClose");
  if (apiKeyBannerClose) {
    apiKeyBannerClose.addEventListener("click", function () {
      if (apiKeyBanner) apiKeyBanner.style.display = "none";
    });
  }

  var BLOCK_EMOJIS = /(🧠|⚠️|💡|🚀|✨|📦|📌|🛠|💻|⚙️)\s*([^\n]*)\n([\s\S]*?)(?=\n\s*(?:🧠|⚠️|💡|🚀|✨|📦|📌|🛠|💻|⚙️)\s*[^\n]*|$)/g;
  var EMOJI_CLASS = { "🧠": "brain", "⚠️": "warn", "💡": "tip", "🚀": "rocket", "✨": "title", "📦": "title", "📌": "problems", "🛠": "suggestions", "💻": "code", "⚙️": "improve" };

  function parseStructuredBlocks(text) {
    BLOCK_EMOJIS.lastIndex = 0;
    var blocks = [];
    var m;
    while ((m = BLOCK_EMOJIS.exec(text)) !== null) {
      var cls = EMOJI_CLASS[m[1]] || "tip";
      blocks.push({ emoji: m[1], title: m[2].trim(), body: m[3].trim(), class: cls });
    }
    return blocks;
  }

  function hasStructuredBlocks(text) {
    return /[🧠⚠️💡🚀✨📦📌🛠💻⚙️]/.test(text);
  }

  function addMessage(text, isYui, isLoading, messageId) {
    var div = document.createElement("div");
    div.className = "msg" + (isYui ? " yui" : " user") + (isLoading ? " loading" : "");
    if (messageId) div.setAttribute("data-message-id", messageId);

    if (isYui && !isLoading && hasStructuredBlocks(text)) {
      var blocks = parseStructuredBlocks(text);
      if (blocks.length) {
        div.classList.add("msg--blocks");
        blocks.forEach(function (b) {
          var block = document.createElement("div");
          block.className = "msg-block msg-block--" + (b.class || "tip");
          var title = document.createElement("div");
          title.className = "msg-block-title";
          title.textContent = b.emoji + " " + (b.title || "");
          block.appendChild(title);
          if (b.body) {
            var body = document.createElement("div");
            body.className = "msg-block-body";
            body.textContent = b.body;
            block.appendChild(body);
          }
          div.appendChild(block);
        });
      } else {
        div.textContent = text;
      }
    } else {
      div.textContent = text;
    }

    if (isYui && !isLoading && messageId) {
      var replyBtn = document.createElement("button");
      replyBtn.type = "button";
      replyBtn.className = "msg-reply-btn reply-btn";
      replyBtn.textContent = "↩";
      replyBtn.setAttribute("data-message-id", messageId);
      var snippet = (text || "").replace(/\s+/g, " ").trim().slice(0, 80);
      if (snippet.length < (text || "").trim().length) snippet += "…";
      replyBtn.setAttribute("data-snippet", snippet);
      replyBtn.addEventListener("click", function () {
        replyToId = this.getAttribute("data-message-id");
        replyToSnippet = this.getAttribute("data-snippet") || "";
        replyPreviewText.textContent = replyToSnippet;
        replyPreview.style.display = "flex";
      });
      div.appendChild(replyBtn);
    }

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
  }

  function clearReplyPreview() {
    replyToId = null;
    replyToSnippet = "";
    replyPreview.style.display = "none";
    replyPreviewText.textContent = "";
  }

  function removeMessage(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  /* Upload como mensagem: selecionou arquivo → card com nome → envia automaticamente */
  fileInput.addEventListener("change", async function () {
    const file = this.files && this.files[0];
    if (!file) return;

    addFileCard(file.name);
    const loadingEl = addMessage("Analisando...", true, true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(API_BASE + "/upload", { method: "POST", body: formData });
      var data;
      try {
        data = await res.json();
      } catch (_) {
        data = { error: "Resposta inválida do servidor (status " + res.status + ")." };
      }
      removeMessage(loadingEl);
      if (data.response != null) {
        addMessage(data.response, true, false, data.message_id || null);
      } else {
        addMessage("Erro: " + (data.error || "Resposta inválida."), true);
      }
    } catch (err) {
      removeMessage(loadingEl);
      addMessage(getNetworkErrorMessage(err), true);
    }

    fileInput.value = "";
  });

  function addFileCard(fileName) {
    var div = document.createElement("div");
    div.className = "msg user file-card";
    div.innerHTML = '<span class="file-card-icon">📎</span><span class="file-card-name">' + escapeHtml(fileName) + "</span>";
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function getNetworkErrorMessage(err) {
    if (window.location.protocol === "file:") {
      return "Não foi possível conectar. Abra o navegador em http://127.0.0.1:5000 e certifique-se de que o servidor está rodando (python web_server.py).";
    }
    return "Erro de rede. Verifique se o servidor está rodando (python web_server.py).";
  }

  replyPreviewCancel.addEventListener("click", clearReplyPreview);

  /* Chat por texto — usa /api/chat/stream (única API de resposta) */
  function getGuestIds() {
    var uid = sessionStorage.getItem("yui_web_guest_id");
    if (!uid) {
      uid = "web-guest-" + Math.random().toString(36).slice(2, 12);
      sessionStorage.setItem("yui_web_guest_id", uid);
    }
    return { user_id: uid, chat_id: sessionStorage.getItem("yui_web_chat_id") };
  }

  function ensureChat() {
    var ids = getGuestIds();
    if (ids.chat_id) return Promise.resolve(ids.chat_id);
    return fetch(API_BASE + "/api/chat/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: ids.user_id }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var cid = data && data.id;
        if (cid) sessionStorage.setItem("yui_web_chat_id", cid);
        return cid;
      });
  }

  function sendText() {
    const text = (msgInput.value || "").trim();
    if (!text) return;

    addMessage(text, false);
    msgInput.value = "";
    const loadingEl = addMessage("Pensando...", true, true);
    clearReplyPreview();

    ensureChat().then(function (chatId) {
      if (!chatId) {
        removeMessage(loadingEl);
        addMessage("Erro ao criar conversa. Use a aplicação principal em /", true);
        return;
      }
      var ids = getGuestIds();
      fetch(API_BASE + "/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, user_id: ids.user_id, message: text }),
      })
        .then(function (response) {
          if (!response.ok || !response.body) throw new Error("Stream failed");
          removeMessage(loadingEl);
          var replyDiv = addMessage("", true, false, null);
          replyDiv.classList.remove("loading");
          var buffer = "";
          return response.body.getReader().then(function (reader) {
            var decoder = new TextDecoder();
            function read() {
              return reader.read().then(function (result) {
                if (result.done) return;
                buffer += decoder.decode(result.value, { stream: true });
                var events = buffer.split("\n\n");
                buffer = events.pop() || "";
                events.forEach(function (event) {
                  var idx = event.indexOf("data: ");
                  if (idx === -1) return;
                  try {
                    var chunk = JSON.parse(event.slice(idx + 6).trim());
                    if (typeof chunk === "string") {
                      if (chunk.indexOf("__STATUS__:") === 0) return;
                      replyDiv.textContent = (replyDiv.textContent || "") + chunk;
                    }
                  } catch (e) {}
                });
                chat.scrollTop = chat.scrollHeight;
                return read();
              });
            }
            return read();
          });
        })
        .catch(function (err) {
          removeMessage(loadingEl);
          addMessage(getNetworkErrorMessage(err), true);
        });
    }).catch(function () {
      removeMessage(loadingEl);
      addMessage(getNetworkErrorMessage(new Error("network")), true);
    });
  }

  sendBtn.addEventListener("click", sendText);
  msgInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText();
    }
  });

  /* Mensagem inicial (sem reply pois não vem da API) */
  addMessage("Olá. Digite uma mensagem ou envie um arquivo (📎) para análise.", true);
})();
