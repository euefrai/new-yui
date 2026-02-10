(function () {
  "use strict";

  var user = null;
  var chatAtual = null;
  var currentChatTitulo = null;
  var supabaseClient = null;

  var loginScreen = document.getElementById("loginScreen");
  var appScreen = document.getElementById("appScreen");
  var userName = document.getElementById("userName");
  var listaChats = document.getElementById("listaChats");
  var chat = document.getElementById("chat");
  var msgInput = document.getElementById("msg");
  var loginForm = document.getElementById("loginForm");
  var loginError = document.getElementById("loginError");
  var loginEmail = document.getElementById("loginEmail");
  var loginPassword = document.getElementById("loginPassword");
  var toggleSignUp = document.getElementById("toggleSignUp");
  var isSignUp = false;
  var userMenu = document.getElementById("userMenu");
  var userMenuName = document.getElementById("userMenuName");
  var userMenuEmail = document.getElementById("userMenuEmail");
  var themeDarkBtn = document.getElementById("themeDarkBtn");
  var themeLightBtn = document.getElementById("themeLightBtn");
  var prefNivel = document.getElementById("prefNivel");
  var prefModo = document.getElementById("prefModo");
  var prefLangs = document.getElementById("prefLangs");
  var saveProfileBtn = document.getElementById("saveProfileBtn");

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function applyTheme(theme) {
    var body = document.body;
    body.classList.remove("theme-light");
    if (theme === "light") {
      body.classList.add("theme-light");
    }
    try {
      localStorage.setItem("yui_theme", theme);
    } catch (e) {}
  }

  function initTheme() {
    var stored = null;
    try {
      stored = localStorage.getItem("yui_theme");
    } catch (e) {}
    if (!stored) stored = "dark";
    applyTheme(stored);
  }

  function initSupabase() {
    var url = window.SUPABASE_URL;
    var key = window.SUPABASE_KEY;
    if (url && key) {
      try {
        supabaseClient = window.supabase.createClient(url, key);
        return true;
      } catch (e) {
        console.warn("Supabase init error", e);
      }
    }
    return false;
  }

  function loadUser() {
    try {
      var stored = localStorage.getItem("yui_user");
      if (stored) {
        user = JSON.parse(stored);
        return true;
      }
    } catch (e) {}
    return false;
  }

  function saveUser(u) {
    user = u;
    if (u) localStorage.setItem("yui_user", JSON.stringify(u));
    else localStorage.removeItem("yui_user");
  }

  function showLogin() {
    if (loginScreen) loginScreen.style.display = "flex";
    if (appScreen) appScreen.style.display = "none";
  }

  function setAvatar() {
    var el = document.getElementById("userAvatar");
    if (!el || !user) return;
    var name = (user.email || user.nome || "U").trim();
    var initial = name.charAt(0).toUpperCase();
    var url = "https://ui-avatars.com/api/?name=" + encodeURIComponent(initial) + "&background=22c55e&color=fff&size=72";
    el.style.backgroundImage = "url(" + url + ")";
    el.setAttribute("title", user.email || "Usuário");
  }

  function showApp() {
    if (loginScreen) loginScreen.style.display = "none";
    if (appScreen) appScreen.style.display = "flex";
    if (userName && user) userName.textContent = user.email || user.nome || "Usuário";
    if (userMenuName && user) userMenuName.textContent = user.email || user.nome || "Usuário";
    if (userMenuEmail && user) userMenuEmail.textContent = user.email || "";
    if (user && user.id) {
      window.USER_ID = user.id;
      if (window.YuiChat && window.YuiChat.setUserId) window.YuiChat.setUserId(user.id);
    }
    setAvatar();
    carregarPerfilUsuario();
    carregarChats();
  }

  function saveLastChatId(id) {
    try {
      if (id) localStorage.setItem("yui_last_chat_id", id);
      else localStorage.removeItem("yui_last_chat_id");
    } catch (e) {}
  }
  window.saveLastChatId = saveLastChatId;

  function getLastChatId() {
    try {
      return localStorage.getItem("yui_last_chat_id");
    } catch (e) {}
    return null;
  }

  function setError(text) {
    if (loginError) loginError.textContent = text || "";
  }

  async function handleAuth() {
    if (!supabaseClient) {
      if (loadUser()) {
        showApp();
        return;
      }
      setError("Supabase não configurado. Configure SUPABASE_URL e SUPABASE_KEY no servidor.");
      showLogin();
      return;
    }

    try {
      var session = (await supabaseClient.auth.getSession()).data.session;
      if (session && session.user) {
        var u = {
          id: session.user.id,
          email: session.user.email || ""
        };
        saveUser(u);
        showApp();
        return;
      }
    } catch (e) {
      console.warn("Auth check error", e);
    }

    if (loadUser()) {
      showApp();
      return;
    }
    showLogin();
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async function (e) {
      e.preventDefault();
      setError("");
      var email = loginEmail.value.trim();
      var password = loginPassword.value;
      if (!email || !password) {
        setError("Preencha e-mail e senha.");
        return;
      }
      if (!supabaseClient) {
        setError("Login não disponível (Supabase não configurado).");
        return;
      }
      try {
        if (isSignUp) {
          var resSignUp = await supabaseClient.auth.signUp({ email: email, password: password });
          if (resSignUp.error) {
            setError(resSignUp.error.message || "Erro ao cadastrar.");
            return;
          }
          setError("Conta criada. Confirme o e-mail ou faça login.");
          return;
        }
        var res = await supabaseClient.auth.signInWithPassword({ email: email, password: password });
        if (res.error) {
          setError(res.error.message || "E-mail ou senha incorretos.");
          return;
        }
        saveUser({ id: res.data.user.id, email: res.data.user.email || "" });
        showApp();
      } catch (err) {
        setError(err.message || "Erro ao entrar.");
      }
    });
  }

  if (toggleSignUp) {
    toggleSignUp.addEventListener("click", function (e) {
      e.preventDefault();
      isSignUp = !isSignUp;
      loginForm.querySelector("button[type=submit]").textContent = isSignUp ? "Cadastrar" : "Entrar";
      setError("");
    });
  }

  var btnSair = document.getElementById("btnSair");
  if (btnSair) btnSair.addEventListener("click", function () {
    if (supabaseClient) {
      supabaseClient.auth.signOut().catch(function () {});
    }
    saveUser(null);
    showLogin();
  });

  if (themeDarkBtn) themeDarkBtn.addEventListener("click", function () { applyTheme("dark"); });
  if (themeLightBtn) themeLightBtn.addEventListener("click", function () { applyTheme("light"); });

  function toggleUserMenu(force) {
    if (!userMenu) return;
    var open = typeof force === "boolean" ? force : !userMenu.classList.contains("open");
    if (open) userMenu.classList.add("open");
    else userMenu.classList.remove("open");
  }

  var userFooter = document.querySelector(".userFooter");
  if (userFooter) {
    userFooter.addEventListener("click", function (e) {
      // Evita que clique no botão sair abra o menu
      if (e.target && e.target.id === "btnSair") return;
      toggleUserMenu();
      e.stopPropagation();
    });
  }

  document.addEventListener("click", function (e) {
    if (!userMenu) return;
    if (!userMenu.classList.contains("open")) return;
    if (userMenu.contains(e.target)) return;
    if (userFooter && userFooter.contains(e.target)) return;
    userMenu.classList.remove("open");
  });

  async function carregarPerfilUsuario() {
    if (!user || !user.id) return;
    try {
      var res = await fetch("/api/user/profile/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id })
      });
      var data = await res.json();
      if (!data || !data.success) return;
      var profile = data.profile || {};
      if (prefNivel) prefNivel.value = profile.nivel_tecnico || "desconhecido";
      if (prefModo) prefModo.value = profile.modo_resposta || "dev";
      if (prefLangs) prefLangs.value = profile.linguagens_pref || "";
    } catch (e) {}
  }

  if (saveProfileBtn) {
    saveProfileBtn.addEventListener("click", async function () {
      if (!user || !user.id) return;
      var body = {
        user_id: user.id,
        email: user.email || "",
        nivel_tecnico: prefNivel ? prefNivel.value : null,
        modo_resposta: prefModo ? prefModo.value : null,
        linguagens_pref: prefLangs ? prefLangs.value : null
      };
      try {
        await fetch("/api/user/profile", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        toggleUserMenu(false);
      } catch (e) {}
    });
  }

  async function carregarChats(skipLoadMessages) {
    if (!user || !user.id) return;
    try {
      var res = await fetch("/get_chats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id })
      });
      var chats = await res.json();
      if (!Array.isArray(chats)) chats = [];
      var lastId = getLastChatId();
      if (lastId && chats.some(function (c) { return c.id === lastId; }) && !chatAtual) {
        chatAtual = lastId;
      }
      listaChats.innerHTML = "";
      chats.forEach(function (c) {
        var div = document.createElement("div");
        div.className = "chatItem" + (chatAtual === c.id ? " ativo" : "");

        var spanTitulo = document.createElement("span");
        spanTitulo.className = "chatTitle";
        spanTitulo.textContent = (c.titulo || "Sem título").slice(0, 30);
        if (chatAtual === c.id) currentChatTitulo = c.titulo || "";

        var btnDelete = document.createElement("button");
        btnDelete.className = "deleteChatBtn";
        btnDelete.title = "Excluir chat";
        btnDelete.textContent = "🗑️";
        btnDelete.addEventListener("click", function (e) {
          e.stopPropagation();
          excluirChat(c.id);
        });

        div.onclick = function () {
          chatAtual = c.id;
          currentChatTitulo = c.titulo || "";
          saveLastChatId(chatAtual);
          carregarChats();
          carregarMensagens();
        };

        div.appendChild(spanTitulo);
        div.appendChild(btnDelete);
        listaChats.appendChild(div);
      });
      if (chatAtual && !skipLoadMessages) {
        carregarMensagens();
      }
    } catch (e) {
      listaChats.innerHTML = "<div class=\"chatItem\">Erro ao carregar</div>";
    }
  }

  async function carregarMensagens() {
    if (!chatAtual) {
      chat.innerHTML = "<div class=\"chatVazio\">Selecione um chat ou crie um novo.</div>";
      return;
    }
    try {
      var res = await fetch("/get_messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatAtual })
      });
      var msgs = await res.json();
      if (!Array.isArray(msgs)) msgs = [];
      chat.innerHTML = "";
      msgs.forEach(function (m) {
        var div = document.createElement("div");
        div.className = "msgBubble " + (m.role === "user" ? "user" : "assistant");
        if (m.id) div.dataset.messageId = m.id;

        if (m.role !== "user" && m.id) {
          var actions = document.createElement("div");
          actions.className = "msgActions";
          var btnEdit = document.createElement("button");
          btnEdit.className = "msgActionBtn";
          btnEdit.type = "button";
          btnEdit.textContent = "✏";
          btnEdit.title = "Editar resposta";
          btnEdit.addEventListener("click", function (e) {
            e.stopPropagation();
            entrarEdicaoMensagem(div);
          });
          var btnImprove = document.createElement("button");
          btnImprove.className = "msgActionBtn";
          btnImprove.type = "button";
          btnImprove.textContent = "✨";
          btnImprove.title = "Melhorar código/resposta";
          btnImprove.addEventListener("click", function (e) {
            e.stopPropagation();
            melhorarMensagem(div);
          });
          actions.appendChild(btnEdit);
          actions.appendChild(btnImprove);
          div.appendChild(actions);
        }

        var content = document.createElement("div");
        content.className = "msgContent";
        content.textContent = m.content || "";
        div.appendChild(content);
        chat.appendChild(div);
      });
      chat.scrollTop = chat.scrollHeight;
    } catch (e) {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao carregar mensagens.</div>";
    }
  }

  function gerarIdLocal() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  async function criarNovoChat() {
    if (!user || !user.id) return null;
    try {
      var res = await fetch("/create_chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id })
      });
      var novo = await res.json();
      if (novo && novo.id) {
        return novo.id;
      }
    } catch (e) {}
    return gerarIdLocal();
  }

  async function excluirChat(chatId) {
    if (!user || !user.id) return;
    try {
      var res = await fetch("/delete_chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id, chat_id: chatId })
      });
      var data = await res.json();
      if (!res.ok || !data || data.success === false) {
        console.error("Erro ao excluir chat:", (data && data.error) || res.statusText);
        return;
      }
      if (chatAtual === chatId) {
        chatAtual = null;
        currentChatTitulo = null;
        saveLastChatId(null);
        if (chat) {
          chat.innerHTML = "<div class=\"chatVazio\">Selecione um chat ou crie um novo.</div>";
        }
      }
      carregarChats(true);
    } catch (e) {
      console.error("Erro ao excluir chat:", e);
    }
  }

  function entrarEdicaoMensagem(bubble) {
    if (!bubble || bubble.classList.contains("editing")) return;
    var messageId = bubble.dataset.messageId;
    if (!messageId) return;
    var content = bubble.querySelector(".msgContent");
    if (!content) return;
    var original = content.textContent || "";
    bubble.classList.add("editing");
    bubble.__originalText = original;

    content.innerHTML = "";
    var textarea = document.createElement("textarea");
    textarea.className = "msgEditArea";
    textarea.value = original;
    content.appendChild(textarea);

    var actions = document.createElement("div");
    actions.className = "msgEditActions";
    var btnSave = document.createElement("button");
    btnSave.type = "button";
    btnSave.className = "msgEditBtn save";
    btnSave.textContent = "Salvar";
    var btnCancel = document.createElement("button");
    btnCancel.type = "button";
    btnCancel.className = "msgEditBtn cancel";
    btnCancel.textContent = "Cancelar";
    actions.appendChild(btnSave);
    actions.appendChild(btnCancel);
    content.appendChild(actions);

    btnSave.addEventListener("click", function () {
      var novo = textarea.value.trim();
      if (!novo) return;
      fetch("/edit_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, action: "edit", new_content: novo })
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.content) {
            content.innerHTML = "";
            var finalText = document.createElement("div");
            finalText.className = "msgContent";
            finalText.textContent = data.content;
            bubble.classList.remove("editing");
            bubble.__originalText = null;
            bubble.appendChild(finalText);
          }
        })
        .catch(function () {});
    });

    btnCancel.addEventListener("click", function () {
      content.innerHTML = "";
      var finalText = document.createElement("div");
      finalText.className = "msgContent";
      finalText.textContent = original;
      bubble.classList.remove("editing");
      bubble.__originalText = null;
      bubble.appendChild(finalText);
    });
  }

  function melhorarMensagem(bubble) {
    var messageId = bubble && bubble.dataset ? bubble.dataset.messageId : null;
    if (!messageId) return;
    var content = bubble.querySelector(".msgContent");
    if (!content) return;
    var original = content.textContent || "";

    content.textContent = "✨ Melhorando resposta...";
    fetch("/edit_message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId, action: "improve" })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.content) {
          content.textContent = data.content;
        } else if (data && data.error) {
          content.textContent = original + "\n\n(Erro ao melhorar: " + data.error + ")";
        } else {
          content.textContent = original;
        }
      })
      .catch(function () {
        content.textContent = original + "\n\n(Erro ao melhorar resposta.)";
      });
  }

  document.getElementById("novoChat").addEventListener("click", async function () {
    if (!user || !user.id) return;
    var id = await criarNovoChat();
    if (id) {
      chatAtual = id;
      currentChatTitulo = "Novo chat";
      saveLastChatId(chatAtual);
      carregarChats();
      chat.innerHTML = "<div class=\"chatVazio\">Novo chat. Envie uma mensagem.</div>";
    } else {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao criar chat. Tente de novo.</div>";
    }
  });

  function isNovoChatTitulo(titulo) {
    return (titulo || "").toLowerCase() === "novo chat";
  }

  function atualizarTituloChat(chatId, firstMessage) {
    fetch("/generate_chat_title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, first_message: firstMessage })
    }).then(function () {
      carregarChats(true);
    }).catch(function () {});
  }

  function enviar() {
    var texto = (msgInput.value || "").trim();
    if (!texto) return;
    if (!user || !user.id) {
      chat.innerHTML = "<div class=\"chatVazio\">Faça login para enviar mensagens.</div>";
      return;
    }

    function fazerEnvio(chatId) {
      chatAtual = chatId;
      currentChatTitulo = "Novo chat";
      saveLastChatId(chatAtual);
      if (!listaChats.querySelector(".chatItem.ativo")) carregarChats();

      var userBubble = document.createElement("div");
    userBubble.className = "msgBubble user";
    userBubble.textContent = texto;
    chat.appendChild(userBubble);
    chat.scrollTop = chat.scrollHeight;

    var assistantBubble = document.createElement("div");
    assistantBubble.className = "msgBubble assistant";
    var statusLine = document.createElement("div");
    statusLine.className = "assistantStatus";
    statusLine.textContent = "🧠 Pensando...";
    var cursor = document.createElement("span");
    cursor.className = "cursorStream";
    assistantBubble.appendChild(statusLine);
    assistantBubble.appendChild(cursor);
    chat.appendChild(assistantBubble);
    chat.scrollTop = chat.scrollHeight;

    msgInput.value = "";
    var btnEnviar = document.getElementById("btnEnviar");
    if (btnEnviar) btnEnviar.disabled = true;

    fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, message: texto })
    })
      .then(function (response) {
        if (!response.ok || !response.body) throw new Error("Stream failed");
        return response.body.getReader();
      })
      .then(function (reader) {
        var decoder = new TextDecoder();
        var buffer = "";
        function read() {
          return reader.read().then(function (result) {
            if (result.done) {
              cursor.remove();
              if (btnEnviar) btnEnviar.disabled = false;
              if (isNovoChatTitulo(currentChatTitulo)) {
                atualizarTituloChat(chatId, texto);
              }
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            var events = buffer.split("\n\n");
            buffer = events.pop() || "";
            events.forEach(function (event) {
              var idx = event.indexOf("data: ");
              if (idx !== -1) {
                try {
                  var payload = event.slice(idx + 6).trim();
                  if (!payload) return;
                  var chunk = JSON.parse(payload);
                  if (typeof chunk === "string" && chunk.indexOf("__STATUS__:") === 0) {
                    if (!statusLine) return;
                    var state = chunk.slice("__STATUS__:".length);
                    if (state === "thinking") {
                      statusLine.textContent = "🧠 Pensando...";
                    } else if (state === "analyzing_code") {
                      statusLine.textContent = "🔎 Analisando código...";
                    } else if (state === "done") {
                      statusLine.remove();
                      statusLine = null;
                    }
                    return;
                  }
                  var textNode = document.createTextNode(chunk);
                  assistantBubble.insertBefore(textNode, cursor);
                } catch (e) {}
              }
            });
            chat.scrollTop = chat.scrollHeight;
            return read();
          });
        }
        return read();
      })
      .catch(function () {
        cursor.remove();
        assistantBubble.textContent = "Erro de rede ou streaming não disponível.";
        if (btnEnviar) btnEnviar.disabled = false;
        chat.scrollTop = chat.scrollHeight;
      });
    }

    if (chatAtual) {
      fazerEnvio(chatAtual);
      return;
    }
    criarNovoChat().then(function (id) {
      if (id) {
        fazerEnvio(id);
      } else {
        chat.innerHTML = "<div class=\"chatVazio\">Erro ao criar chat. Tente clicar em «+ Novo chat» primeiro.</div>";
      }
    });
  }

  var btnEnviarEl = document.getElementById("btnEnviar");
  if (btnEnviarEl) btnEnviarEl.addEventListener("click", function (e) { e.preventDefault(); enviar(); });
  if (msgInput) msgInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  });

  var fileInput = document.getElementById("fileInput");
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      var f = this.files && this.files[0];
      if (!f || !chat) return;
      var fileName = f.name || "arquivo";
      var userBubble = document.createElement("div");
      userBubble.className = "msgBubble user";
      userBubble.textContent = "📎 Arquivo: " + fileName;
      if (chat.querySelector(".chatVazio")) chat.innerHTML = "";
      chat.appendChild(userBubble);
      var assistantBubble = document.createElement("div");
      assistantBubble.className = "msgBubble assistant";
      assistantBubble.textContent = "Analisando...";
      chat.appendChild(assistantBubble);
      chat.scrollTop = chat.scrollHeight;
      var formData = new FormData();
      formData.append("file", f);
      fetch("/upload", { method: "POST", body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          assistantBubble.textContent = data.response || data.error || "Erro ao analisar o arquivo.";
          chat.scrollTop = chat.scrollHeight;
        })
        .catch(function () {
          assistantBubble.textContent = "Erro de conexão ao enviar o arquivo.";
          chat.scrollTop = chat.scrollHeight;
        });
      fileInput.value = "";
    });
  }

  initSupabase();
  initTheme();
  handleAuth();
})();
