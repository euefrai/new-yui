/**
 * Chat usando a API central (core): /api/chats, /api/chat/new, /api/messages, /api/send
 * Depende de window.USER_ID (definido por app.js ao carregar usuário)
 */
(function () {
  "use strict";

  var currentChat = null;
  var user_id = window.USER_ID || null;

  function getListaChats() { return document.getElementById("listaChats"); }
  function getChat() { return document.getElementById("chat"); }
  function getMsgInput() { return document.getElementById("msg"); }

  function addMessage(role, text) {
    var chat = getChat();
    if (!chat) return;
    var div = document.createElement("div");
    div.className = "msgBubble chat-bubble " + (role === "user" ? "user" : "assistant");
    div.textContent = text || "";
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  async function loadChats() {
    if (!user_id) return;
    var lista = getListaChats();
    if (!lista) return;
    try {
      var res = await fetch((window.apiUrl || function(p){return p;})("/api/chats/" + encodeURIComponent(user_id)));
      var chats = await res.json();
      if (!Array.isArray(chats)) chats = [];
      lista.innerHTML = "";
      chats.forEach(function (c) {
        var div = document.createElement("div");
        div.className = "chatItem" + (currentChat === c.id ? " ativo" : "");
        div.textContent = (c.titulo || c.title || "Sem título").slice(0, 30);
        div.onclick = function () {
          currentChat = c.id;
          if (window.saveLastChatId) window.saveLastChatId(c.id);
          loadMessages();
          loadChats();
        };
        lista.appendChild(div);
      });
    } catch (e) {
      lista.innerHTML = "<div class=\"chatItem\">Erro ao carregar</div>";
    }
  }

  async function loadMessages() {
    var chat = getChat();
    if (!chat) return;
    if (!currentChat) {
      chat.innerHTML = "<div class=\"chatVazio\">Selecione um chat ou crie um novo.</div>";
      return;
    }
    try {
      var res = await fetch((window.apiUrl || function(p){return p;})("/api/messages/" + encodeURIComponent(currentChat)));
      var msgs = await res.json();
      if (!Array.isArray(msgs)) msgs = [];
      chat.innerHTML = "";
      msgs.forEach(function (m) {
        addMessage(m.role || "user", m.content || "");
      });
      chat.scrollTop = chat.scrollHeight;
    } catch (e) {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao carregar mensagens.</div>";
    }
  }

  async function newChat() {
    if (!user_id) return;
    try {
      var res = await fetch((window.apiUrl || function(p){return p;})("/api/chat/new"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user_id })
      });
      var chat = await res.json();
      if (chat && chat.id) {
        currentChat = chat.id;
        if (window.saveLastChatId) window.saveLastChatId(chat.id);
        loadChats();
        loadMessages();
      }
    } catch (e) {
      console.warn("newChat error", e);
    }
  }

  async function sendMessage() {
    if (!currentChat || !user_id) return;
    var input = getMsgInput();
    var text = (input && input.value || "").trim();
    if (!text) return;
    if (input) input.value = "";
    try {
      var res = await fetch((window.apiUrl || function(p){return p;})("/api/send"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user_id,
          chat_id: currentChat,
          message: text
        })
      });
      var data = await res.json();
      addMessage("user", text);
      addMessage("assistant", data.reply != null ? data.reply : (data.error || "Erro ao obter resposta."));
    } catch (e) {
      addMessage("user", text);
      addMessage("assistant", "Erro de conexão.");
    }
  }

  function setUserId(id) {
    user_id = id;
    window.USER_ID = id;
  }

  window.YuiChat = {
    setUserId: setUserId,
    get currentChat() { return currentChat; },
    set currentChat(id) { currentChat = id; },
    newChat: newChat,
    sendMessage: sendMessage,
    loadChats: loadChats,
    loadMessages: loadMessages,
    addMessage: addMessage
  };
})();
