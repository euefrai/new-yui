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

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
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
    setAvatar();
    carregarChats();
  }

  function saveLastChatId(id) {
    try {
      if (id) localStorage.setItem("yui_last_chat_id", id);
      else localStorage.removeItem("yui_last_chat_id");
    } catch (e) {}
  }

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

  document.getElementById("btnSair").addEventListener("click", function () {
    if (supabaseClient) {
      supabaseClient.auth.signOut().catch(function () {});
    }
    saveUser(null);
    showLogin();
  });

  async function carregarChats() {
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
        div.textContent = (c.titulo || "Sem título").slice(0, 30);
        if (chatAtual === c.id) currentChatTitulo = c.titulo || "";
        div.onclick = function () {
          chatAtual = c.id;
          currentChatTitulo = c.titulo || "";
          saveLastChatId(chatAtual);
          carregarChats();
          carregarMensagens();
        };
        listaChats.appendChild(div);
      });
      if (chatAtual) {
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
        div.textContent = m.content || "";
        chat.appendChild(div);
      });
      chat.scrollTop = chat.scrollHeight;
    } catch (e) {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao carregar mensagens.</div>";
    }
  }

  document.getElementById("novoChat").addEventListener("click", async function () {
    if (!user || !user.id) return;
    try {
      var res = await fetch("/create_chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id })
      });
      var novo = await res.json();
      if (novo && novo.id) {
        chatAtual = novo.id;
        currentChatTitulo = "Novo chat";
        saveLastChatId(chatAtual);
        carregarChats();
        chat.innerHTML = "<div class=\"chatVazio\">Novo chat. Envie uma mensagem.</div>";
      }
    } catch (e) {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao criar chat.</div>";
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
      carregarChats();
    }).catch(function () {});
  }

  function enviar() {
    var texto = (msgInput.value || "").trim();
    if (!texto) return;
    if (!chatAtual) {
      chat.innerHTML = "<div class=\"chatVazio\">Crie ou selecione um chat primeiro.</div>";
      return;
    }

    var userBubble = document.createElement("div");
    userBubble.className = "msgBubble user";
    userBubble.textContent = texto;
    chat.appendChild(userBubble);
    chat.scrollTop = chat.scrollHeight;

    var assistantBubble = document.createElement("div");
    assistantBubble.className = "msgBubble assistant";
    var cursor = document.createElement("span");
    cursor.className = "cursorStream";
    assistantBubble.appendChild(cursor);
    chat.appendChild(assistantBubble);
    chat.scrollTop = chat.scrollHeight;

    msgInput.value = "";
    var btnEnviar = document.getElementById("btnEnviar");
    if (btnEnviar) btnEnviar.disabled = true;

    fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatAtual, message: texto })
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
                atualizarTituloChat(chatAtual, texto);
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

  document.getElementById("btnEnviar").addEventListener("click", enviar);
  msgInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviar();
    }
  });

  initSupabase();
  handleAuth();
})();
