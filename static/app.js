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
  var previewPanel = document.getElementById("previewPanel");
  var previewFrame = document.getElementById("previewFrame");
  var previewTitle = document.getElementById("previewTitle");
  var closePreview = document.getElementById("closePreview");
  var pendingFile = null;
  var pendingFileName = "";
  var fileBadge = null;
  var messagesAbortController = null;
  var messagesCache = {};
  var currentModel = "yui";

  function getCurrentModel() {
    var sel = document.getElementById("modelSwitcher");
    return (sel && sel.value) ? sel.value : "yui";
  }

  function applyModelVisual(model) {
    currentModel = model;
    var appContent = document.getElementById("appContent");
    var inputArea = document.getElementById("inputArea");
    if (appContent) appContent.setAttribute("data-model", model);
    if (inputArea) inputArea.setAttribute("data-model", model);
    document.body.classList.toggle("model-heathcliff", model === "heathcliff");
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function stripJsonWrapper(text) {
    if (!text || typeof text !== "string") return text;
    var s = text.trim();
    if (s.indexOf("{\"mode\":\"answer\"") !== 0 && s.indexOf('{"mode":"answer"') !== 0) return text;
    try {
      var parsed = JSON.parse(s);
      if (parsed && typeof parsed.answer === "string") return parsed.answer;
    } catch (e) {}
    return text;
  }

  function formatMarkdownToHtml(text) {
    if (!text || typeof text !== "string") return "";
    text = stripJsonWrapper(text);
    var parts = [];
    var rest = text;
    var codeBlockRe = /```(\w*)\n([\s\S]*?)```/g;
    var lastIndex = 0;
    var match;
    while ((match = codeBlockRe.exec(rest)) !== null) {
      var before = rest.slice(lastIndex, match.index);
      if (before) parts.push(escapeHtml(before).replace(/\n/g, "<br>"));
      var lang = match[1] || "text";
      var rawCode = match[2].replace(/\r\n/g, "\n").trim();
      var code = escapeHtml(rawCode);
      parts.push('<div class="codeBlockWrap" data-lang="' + escapeHtml(lang) + '"><div class="codeBlockHeader"><span class="codeBlockLang">' + escapeHtml(lang) + '</span><button type="button" class="codeBlockCopy" title="Copiar código">Copiar código</button><button type="button" class="codeBlockToWorkspace" title="Enviar para o Workspace">Enviar para o Workspace</button></div><pre><code class="language-' + escapeHtml(lang) + '">' + code + '</code></pre></div>');
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < rest.length) parts.push(escapeHtml(rest.slice(lastIndex)).replace(/\n/g, "<br>"));
    if (parts.length === 0) return escapeHtml(rest).replace(/\n/g, "<br>");
    return parts.join("");
  }

  function initDownloadButtons(container, rawText) {
    if (!container) return;
    var text = rawText || (container.textContent || "").replace(/\s+/g, " ");
    var match = text.match(/\[DOWNLOAD\]:(\S+)/);
    if (!match) return;
    var url = match[1];
    var existing = container.querySelector(".download-btn, .btn-download");
    if (existing) return;
    var link = document.createElement("a");
    link.href = url;
    link.innerText = "⬇️ Baixar Projeto";
    link.className = "download-btn btn-download";
    link.target = "_blank";
    link.rel = "noopener";
    var filename = url.split("/").pop() || "projeto.zip";
    if (filename) link.setAttribute("download", filename);
    container.appendChild(link);
  }

  function finalizeAssistantBubble(bubble) {
    if (!bubble) return;
    var fullText = bubble.textContent || "";
    var cleaned = fullText.replace(/\n?\[DOWNLOAD\]:\S+/, "").trim();
    bubble.innerHTML = formatMarkdownToHtml(cleaned);
    attachCodeBlockCopyButtons(bubble);
    initDownloadButtons(bubble, fullText);
    if (typeof window.hljs !== "undefined") {
      bubble.querySelectorAll("pre code").forEach(function (el) {
        try { window.hljs.highlightElement(el); } catch (e) {}
      });
    }
    applyModelVisual(getCurrentModel());
  }

  function attachCodeBlockCopyButtons(container) {
    if (!container) return;
    container.querySelectorAll(".codeBlockCopy").forEach(function (btn) {
      if (btn._copyAttached) return;
      btn._copyAttached = true;
      btn.addEventListener("click", function () {
        var pre = btn.closest(".codeBlockWrap");
        if (!pre) return;
        var code = pre.querySelector("code");
        if (!code) return;
        try {
          navigator.clipboard.writeText(code.textContent);
          var orig = btn.textContent;
          btn.textContent = "Copiado!";
          setTimeout(function () { btn.textContent = orig; }, 1500);
        } catch (e) {}
      });
    });
    container.querySelectorAll(".codeBlockToWorkspace").forEach(function (btn) {
      if (btn._workspaceAttached) return;
      btn._workspaceAttached = true;
      btn.addEventListener("click", function () {
        var wrap = btn.closest(".codeBlockWrap");
        if (!wrap) return;
        var codeEl = wrap.querySelector("code");
        var lang = wrap.getAttribute("data-lang") || "text";
        if (!codeEl) return;
        var code = codeEl.textContent || "";
        if (window.updateEditor) window.updateEditor(code, lang);
      });
    });
  }

  function openPreview(url, title) {
    if (!previewPanel || !previewFrame) return;
    previewFrame.src = url || "about:blank";
    if (previewTitle) previewTitle.textContent = title || "Preview";
    previewPanel.classList.add("open");
  }

  function closePreviewPanel() {
    if (!previewPanel || !previewFrame) return;
    previewPanel.classList.remove("open");
    previewFrame.src = "about:blank";
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

  var workspaceOpen = true;
  function getWorkspacePref() {
    try {
      var v = localStorage.getItem("yui_workspace_open");
      return v === null ? true : v === "true";
    } catch (e) { return true; }
  }
  function setWorkspacePref(open) {
    try { localStorage.setItem("yui_workspace_open", String(open)); } catch (e) {}
  }
  function toggleWorkspace() {
    workspaceOpen = !workspaceOpen;
    setWorkspacePref(workspaceOpen);
    var mainSplit = document.querySelector(".mainSplit");
    var btn = document.getElementById("toggleWorkspace");
    if (mainSplit) {
      mainSplit.classList.toggle("workspaceCollapsed", !workspaceOpen);
      mainSplit.classList.toggle("editor-hidden", !workspaceOpen);
    }
    if (btn) btn.classList.toggle("workspaceClosed", !workspaceOpen);
    if (workspaceOpen) setTimeout(function () { window.dispatchEvent(new Event("resize")); }, 420);
  }
  function initWorkspaceToggle() {
    workspaceOpen = getWorkspacePref();
    var mainSplit = document.querySelector(".mainSplit");
    var btn = document.getElementById("toggleWorkspace");
    if (mainSplit) {
      mainSplit.classList.toggle("workspaceCollapsed", !workspaceOpen);
      mainSplit.classList.toggle("editor-hidden", !workspaceOpen);
    }
    if (btn) btn.classList.toggle("workspaceClosed", !workspaceOpen);
    if (btn) btn.addEventListener("click", toggleWorkspace);
    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.key === "l") {
        e.preventDefault();
        toggleWorkspace();
      }
    });
  }

  function showApp() {
    if (loginScreen) loginScreen.style.display = "none";
    if (appScreen) appScreen.style.display = "flex";
    initWorkspaceToggle();
    if (window.initYuiWorkspace) window.initYuiWorkspace();
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

  /** Atualiza chatAtual + título, persiste em localStorage. Não carrega mensagens. */
  function setChatAtual(id, titulo) {
    chatAtual = id;
    currentChatTitulo = (titulo != null && titulo !== undefined) ? titulo : (id ? "Novo chat" : null);
    saveLastChatId(chatAtual);
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
      setError("Supabase não configurado. Configure SUPABASE_URL e SUPABASE_ANON_KEY no servidor.");
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

  var clearChatBtn = document.getElementById("clearChat");
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", async function () {
      try {
        var body = {};
        if (user && user.id) body.user_id = user.id;
        await fetch("/clear_chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } catch (e) {}
      location.reload();
    });
  }

  if (themeDarkBtn) themeDarkBtn.addEventListener("click", function () { applyTheme("dark"); });
  if (themeLightBtn) themeLightBtn.addEventListener("click", function () { applyTheme("light"); });
  if (closePreview) closePreview.addEventListener("click", function () { closePreviewPanel(); });

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
      var res = await fetch("/api/chats/" + encodeURIComponent(user.id));
      var chats = await res.json();
      if (!Array.isArray(chats)) chats = [];
      var lastId = getLastChatId();
      if (lastId && chats.some(function (c) { return c.id === lastId; }) && !chatAtual) {
        var found = chats.find(function (x) { return x.id === lastId; });
        setChatAtual(lastId, found ? found.titulo : null);
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
          setChatAtual(c.id, c.titulo);
          carregarChats(true);
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

  function renderMensagensNoChat(msgs) {
    if (!chat) return;
    chat.innerHTML = "";
    if (!Array.isArray(msgs) || msgs.length === 0) {
      chat.scrollTop = 0;
      return;
    }
    msgs.forEach(function (m) {
      var div = document.createElement("div");
      div.className = "msgBubble " + (m.role === "user" ? "user" : "assistant");
      if (m.id) div.dataset.messageId = m.id;

      if (m.id) {
        var actions = document.createElement("div");
        actions.className = "msgActions";

        var btnReply = document.createElement("button");
        btnReply.className = "msgActionBtn";
        btnReply.type = "button";
        btnReply.textContent = "↩";
        btnReply.title = "Responder";
        btnReply.addEventListener("click", function (e) {
          e.stopPropagation();
          responderMensagem(div);
        });

        var btnImprove = document.createElement("button");
        btnImprove.className = "msgActionBtn";
        btnImprove.type = "button";
        btnImprove.textContent = "✨";
        btnImprove.title = "Melhorar mensagem";
        btnImprove.addEventListener("click", function (e) {
          e.stopPropagation();
          melhorarMensagem(div);
        });

        var btnDelete = document.createElement("button");
        btnDelete.className = "msgActionBtn";
        btnDelete.type = "button";
        btnDelete.textContent = "🗑";
        btnDelete.title = "Excluir mensagem";
        btnDelete.addEventListener("click", function (e) {
          e.stopPropagation();
          excluirMensagem(div);
        });

        actions.appendChild(btnReply);
        actions.appendChild(btnImprove);
        actions.appendChild(btnDelete);
        div.appendChild(actions);
      }

      var content = document.createElement("div");
      content.className = "msgContent";
      var raw = m.content || "";
      var previewUrl = null;
      var downloadUrl = null;
      if (m.role === "assistant") {
        var linhas = raw.split("\n");
        var filtradas = [];
        linhas.forEach(function (ln) {
          if (ln.indexOf("[PREVIEW_URL]:") === 0) {
            previewUrl = ln.replace("[PREVIEW_URL]:", "").trim();
          } else if (ln.indexOf("[DOWNLOAD]:") === 0) {
            downloadUrl = ln.replace("[DOWNLOAD]:", "").trim();
          } else {
            filtradas.push(ln);
          }
        });
        raw = filtradas.join("\n");
      }
      if (m.role === "assistant" && raw) {
        content.innerHTML = formatMarkdownToHtml(raw);
        attachCodeBlockCopyButtons(content);
      } else {
        content.textContent = raw;
      }
      div.appendChild(content);

      if (downloadUrl) {
        var link = document.createElement("a");
        link.href = downloadUrl;
        link.innerText = "⬇️ Baixar Projeto";
        link.className = "download-btn btn-download";
        link.target = "_blank";
        link.rel = "noopener";
        var filename = downloadUrl.split("/").pop() || "projeto.zip";
        if (filename) link.setAttribute("download", filename);
        div.appendChild(link);
      }
      if (previewUrl) {
        var btnPrev = document.createElement("button");
        btnPrev.type = "button";
        btnPrev.className = "msgActionBtn";
        btnPrev.style.marginTop = "4px";
        btnPrev.textContent = "▶ Ver resultado";
        btnPrev.addEventListener("click", function (e) {
          e.stopPropagation();
          openPreview(previewUrl, "Preview do projeto");
        });
        div.appendChild(btnPrev);
      }
      chat.appendChild(div);
    });
    if (typeof window.hljs !== "undefined") {
      chat.querySelectorAll("pre code").forEach(function (el) {
        try { window.hljs.highlightElement(el); } catch (e) {}
      });
    }
    applyModelVisual(getCurrentModel());
    chat.scrollTop = chat.scrollHeight;
  }

  function showErroMensagensComRetry() {
    if (!chat) return;
    chat.innerHTML = "<div class=\"chatVazio\">" +
      "Erro ao carregar mensagens. " +
      "<button type=\"button\" class=\"msgEditBtn save\" id=\"retryMessagesBtn\" style=\"margin-top:8px;\">Tentar novamente</button>" +
      "</div>";
    var btn = document.getElementById("retryMessagesBtn");
    if (btn) btn.addEventListener("click", function () { carregarMensagens(); });
  }

  async function carregarMensagens() {
    if (!chatAtual) {
      chat.innerHTML = "<div class=\"chatVazio\">Selecione um chat ou crie um novo.</div>";
      return;
    }
    if (messagesAbortController) {
      messagesAbortController.abort();
    }
    messagesAbortController = new AbortController();
    var loadingFor = chatAtual;
    if (!user || !user.id) {
      chat.innerHTML = "<div class=\"chatVazio\">Faça login para carregar mensagens.</div>";
      return;
    }
    var fromCache = messagesCache[loadingFor];
    if (fromCache && fromCache.length > 0) {
      renderMensagensNoChat(fromCache);
    } else {
      chat.innerHTML = "<div class=\"chatVazio chatLoading\">Carregando mensagens...</div>";
    }
    try {
      var url = "/api/messages/" + encodeURIComponent(loadingFor) + "?user_id=" + encodeURIComponent(user.id);
      var res = await fetch(url, {
        signal: messagesAbortController.signal
      });
      var msgs = await res.json();
      if (loadingFor !== chatAtual) return;
      if (!Array.isArray(msgs)) msgs = [];
      messagesCache[loadingFor] = msgs;
      renderMensagensNoChat(msgs);
    } catch (e) {
      if (e.name === "AbortError") return;
      if (loadingFor === chatAtual) {
        showErroMensagensComRetry();
      }
    } finally {
      if (messagesAbortController && messagesAbortController.signal.aborted === false) {
        messagesAbortController = null;
      }
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
      var res = await fetch("/api/chat/new", {
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
      var res = await fetch("/api/chat/delete", {
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
        setChatAtual(null);
        delete messagesCache[chatId];
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
    if (!user || !user.id) return;
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
      fetch("/api/message/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, user_id: user.id, action: "edit", new_content: novo })
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.content) {
            content.innerHTML = "";
            content.textContent = data.content;
            bubble.classList.remove("editing");
            bubble.__originalText = null;
            if (chatAtual) delete messagesCache[chatAtual];
          }
        })
        .catch(function () {});
    });

    btnCancel.addEventListener("click", function () {
      content.innerHTML = "";
      content.textContent = original;
      bubble.classList.remove("editing");
      bubble.__originalText = null;
    });
  }

  function melhorarMensagem(bubble) {
    if (!user || !user.id) return;
    var messageId = bubble && bubble.dataset ? bubble.dataset.messageId : null;
    if (!messageId) return;
    var content = bubble.querySelector(".msgContent");
    if (!content) return;
    var original = content.textContent || "";

    content.textContent = "✨ Melhorando resposta...";
    fetch("/api/message/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId, user_id: user.id, action: "improve" })
    })
      .then(function (r) { return r.json();     })
      .then(function (data) {
        if (data && data.content) {
          content.textContent = data.content;
          if (chatAtual) delete messagesCache[chatAtual];
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

  function excluirMensagem(bubble) {
    if (!user || !user.id) return;
    var messageId = bubble && bubble.dataset ? bubble.dataset.messageId : null;
    if (!messageId) return;
    fetch("/api/message/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: messageId, user_id: user.id })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.success) {
          bubble.remove();
          if (chatAtual) delete messagesCache[chatAtual];
        }
      })
      .catch(function () {});
  }

  function responderMensagem(bubble) {
    var content = bubble && bubble.querySelector ? bubble.querySelector(".msgContent") : null;
    if (!content || !msgInput) return;
    var texto = (content.textContent || "").trim();
    if (!texto) return;
    var trecho = texto.length > 180 ? texto.slice(0, 177) + "..." : texto;
    msgInput.value = "↩ " + trecho + "\n\n";
    msgInput.focus();
  }

  document.getElementById("novoChat").addEventListener("click", async function () {
    if (!user || !user.id) return;
    var id = await criarNovoChat();
    if (id) {
      setChatAtual(id, "Novo chat");
      carregarChats(true);
      chat.innerHTML = "<div class=\"chatVazio\">Novo chat. Envie uma mensagem.</div>";
    } else {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao criar chat. Tente de novo.</div>";
    }
  });

  function isNovoChatTitulo(titulo) {
    return (titulo || "").toLowerCase() === "novo chat";
  }

  function atualizarTituloChat(chatId, firstMessage) {
    fetch("/api/chat/title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, user_id: user.id, first_message: firstMessage })
    }).then(function () {
      carregarChats(true);
    }).catch(function () {});
  }

  function enviar() {
    var texto = (msgInput.value || "").trim();
    var temArquivo = !!pendingFile;
    var lower = texto.toLowerCase();
    var isProjeto =
      !temArquivo &&
      (lower.includes("mini saas") ||
        lower.includes("mini-saas") ||
        lower.includes("mini projeto") ||
        lower.includes("projeto") ||
        lower.includes("landing page") ||
        lower.includes("landing") ||
        lower.includes("site completo") ||
        lower.includes("site ") ||
        lower.includes("gerar projeto") ||
        lower.includes("gera projeto") ||
        lower.includes("cria um saas") ||
        lower.includes("criar um saas") ||
        lower.includes("gerar ") && (lower.includes("arquivo") || lower.includes("projeto") || lower.includes("site") || lower.includes("app")) ||
        lower.includes("criar ") && (lower.includes("arquivo") || lower.includes("projeto") || lower.includes("site") || lower.includes("app") || lower.includes("página")) ||
        lower.includes("cria ") && (lower.includes("projeto") || lower.includes("site") || lower.includes("app")) ||
        lower.includes("gera ") && (lower.includes("projeto") || lower.includes("site") || lower.includes("app")) ||
        lower.includes("página web") ||
        lower.includes("criar projeto") ||
        lower.includes("gerar arquivos") ||
        lower.includes("create project") ||
        lower.includes("generate project") ||
        lower.includes("build a ") ||
        lower.includes("make a project"));
    if (!texto && !temArquivo) return;
    if (!user || !user.id) {
      chat.innerHTML = "<div class=\"chatVazio\">Faça login para enviar mensagens.</div>";
      return;
    }

    function fazerEnvio(chatId) {
      setChatAtual(chatId, currentChatTitulo || "Novo chat");
      delete messagesCache[chatId];
      if (!listaChats.querySelector(".chatItem.ativo")) carregarChats(true);

      var userBubble = document.createElement("div");
      userBubble.className = "msgBubble user";
      userBubble.textContent = texto || (temArquivo ? "📎 Arquivo enviado" : "");
      if (temArquivo && pendingFileName) {
        var tag = document.createElement("div");
        tag.className = "fileTag";
        tag.textContent = "📎 " + pendingFileName;
        userBubble.appendChild(tag);
      }
      chat.appendChild(userBubble);
    chat.scrollTop = chat.scrollHeight;

      var btnEnviar = document.getElementById("btnEnviar");
      msgInput.value = "";

      if (temArquivo && pendingFile) {
        // Fluxo de análise de arquivo junto com a mensagem
        var assistantBubble = document.createElement("div");
        assistantBubble.className = "msgBubble assistant";
        assistantBubble.textContent = "🔎 Analisando arquivo...";
        chat.appendChild(assistantBubble);
        chat.scrollTop = chat.scrollHeight;

        var formData = new FormData();
        formData.append("file", pendingFile);
        fetch("/api/upload", { method: "POST", body: formData })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            assistantBubble.textContent = data.response || data.error || "Erro ao analisar o arquivo.";
            chat.scrollTop = chat.scrollHeight;
          })
          .catch(function () {
            assistantBubble.textContent = "Erro de conexão ao enviar o arquivo.";
            chat.scrollTop = chat.scrollHeight;
          })
          .finally(function () {
            pendingFile = null;
            pendingFileName = "";
            if (fileBadge) fileBadge.remove();
            fileBadge = null;
            if (fileInput) fileInput.value = "";
            if (btnEnviar) btnEnviar.disabled = false;
          });
      } else if (isProjeto) {
        var assistantBubble2 = document.createElement("div");
        assistantBubble2.className = "msgBubble assistant";
        assistantBubble2.textContent = "🧱 Criando estrutura do projeto...";
        chat.appendChild(assistantBubble2);
        chat.scrollTop = chat.scrollHeight;

        if (btnEnviar) btnEnviar.disabled = true;

        fetch("/api/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: user.id, chat_id: chatId, message: texto, model: getCurrentModel() })
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            var reply = (data && data.reply) || (data && data.error) || "Erro ao gerar o projeto.";
            assistantBubble2.textContent = reply;
            chat.scrollTop = chat.scrollHeight;
            if (isNovoChatTitulo(currentChatTitulo)) {
              atualizarTituloChat(chatId, texto);
            }
            fetchTelemetry();
            // recarrega mensagens para aplicar botão de preview, se houver
            carregarMensagens();
          })
          .catch(function () {
            assistantBubble2.textContent = "Erro de rede ao gerar o projeto.";
            chat.scrollTop = chat.scrollHeight;
          })
          .finally(function () {
            if (btnEnviar) btnEnviar.disabled = false;
          });
      } else {
        var assistantBubble = document.createElement("div");
        assistantBubble.className = "msgBubble assistant";
        assistantBubble.setAttribute("data-status", "sending");
        var statusLine = document.createElement("div");
        statusLine.className = "assistantStatus";
        statusLine.textContent = "🧠 Pensando...";
        var cursor = document.createElement("span");
        cursor.className = "cursorStream";
        assistantBubble.appendChild(statusLine);
        assistantBubble.appendChild(cursor);
        chat.appendChild(assistantBubble);
        chat.scrollTop = chat.scrollHeight;

        if (btnEnviar) btnEnviar.disabled = true;

        fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chat_id: chatId, user_id: user.id, message: texto, model: getCurrentModel() })
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
                  assistantBubble.setAttribute("data-status", "sent");
                  finalizeAssistantBubble(assistantBubble);
                  if (btnEnviar) btnEnviar.disabled = false;
                  if (isNovoChatTitulo(currentChatTitulo)) {
                    atualizarTituloChat(chatId, texto);
                  }
                  fetchTelemetry();
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
                          assistantBubble.setAttribute("data-status", "sending");
                        } else if (state === "analyzing_code") {
                          statusLine.textContent = "🔎 Analisando código...";
                          assistantBubble.setAttribute("data-status", "streaming");
                        } else if (state === "done") {
                          statusLine.remove();
                          statusLine = null;
                          assistantBubble.setAttribute("data-status", "sent");
                          if (cursor && cursor.parentNode) cursor.remove();
                          finalizeAssistantBubble(assistantBubble);
                        }
                        return;
                      }
                      assistantBubble.setAttribute("data-status", "streaming");
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
            assistantBubble.setAttribute("data-status", "error");
            assistantBubble.textContent = "Erro de rede ou streaming não disponível. Tente novamente.";
            if (btnEnviar) btnEnviar.disabled = false;
            chat.scrollTop = chat.scrollHeight;
          });
      }
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

  var modelSwitcher = document.getElementById("modelSwitcher");
  if (modelSwitcher) {
    modelSwitcher.addEventListener("change", function () {
      applyModelVisual(getCurrentModel());
      try { localStorage.setItem("yui_model", getCurrentModel()); } catch (e) {}
    });
    var saved = "";
    try { saved = localStorage.getItem("yui_model") || ""; } catch (e) {}
    if (saved === "heathcliff") {
      modelSwitcher.value = "heathcliff";
      applyModelVisual("heathcliff");
    }
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
      if (!f) return;
      pendingFile = f;
      pendingFileName = f.name || "arquivo";
      if (!fileBadge) {
        fileBadge = document.createElement("div");
        fileBadge.className = "fileAttached";
        var icon = document.createElement("span");
        icon.textContent = "📎";
        var nameSpan = document.createElement("span");
        nameSpan.id = "fileAttachedName";
        fileBadge.appendChild(icon);
        fileBadge.appendChild(nameSpan);
        var app = document.getElementById("appScreen");
        if (app) app.appendChild(fileBadge);
      }
      var nameSpanEl = document.getElementById("fileAttachedName");
      if (nameSpanEl) nameSpanEl.textContent = pendingFileName;
      fileBadge.onclick = function () {
        pendingFile = null;
        pendingFileName = "";
        if (fileBadge) fileBadge.remove();
        fileBadge = null;
        fileInput.value = "";
      };
    });
  }

  function fetchSystemHealth() {
    fetch("/api/system/health")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var bar = document.getElementById("systemHealthBar");
        var indicator = document.getElementById("systemHealthIndicator");
        var label = document.getElementById("systemHealthLabel");
        if (!bar || !indicator || !label) return;
        if (!data.available) {
          bar.setAttribute("data-mode", "unavailable");
          label.textContent = "Sistema: monitoramento indisponível";
          return;
        }
        var mode = data.mode || "normal";
        bar.setAttribute("data-mode", mode);
        var cpu = data.cpu_percent || 0;
        var ram = data.ram_percent || 0;
        label.textContent = "Sistema: CPU " + cpu + "% | RAM " + ram + "%" + (mode !== "normal" ? " • Modo economia" : "");
      })
      .catch(function () {
        var bar = document.getElementById("systemHealthBar");
        var label = document.getElementById("systemHealthLabel");
        if (bar && label) {
          bar.setAttribute("data-mode", "unavailable");
          label.textContent = "Sistema: —";
        }
      });
  }

  function fetchTelemetry() {
    fetch("/api/system/telemetry")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var costEl = document.getElementById("telemetryCost");
        var reqEl = document.getElementById("telemetryRequests");
        if (costEl) costEl.textContent = (data.cost_estimate != null ? "R$ " + data.cost_estimate.toFixed(2) : "—");
        if (reqEl) reqEl.textContent = (data.requests != null ? data.requests : "—");
      })
      .catch(function () {
        var costEl = document.getElementById("telemetryCost");
        var reqEl = document.getElementById("telemetryRequests");
        if (costEl) costEl.textContent = "—";
        if (reqEl) reqEl.textContent = "—";
      });
  }

  var systemPollingStarted = false;
  function startSystemPolling() {
    if (systemPollingStarted) return;
    systemPollingStarted = true;
    fetchSystemHealth();
    fetchTelemetry();
    setInterval(fetchSystemHealth, 8000);
    setInterval(fetchTelemetry, 15000);
  }

  var originalShowApp = showApp;
  showApp = function () {
    originalShowApp();
    startSystemPolling();
  };

  initSupabase();
  initTheme();
  handleAuth();
})();
