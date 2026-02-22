(function () {
  "use strict";

  function apiUrl(path) {
    var p = String(path || "").trim();
    if (!p) return "/";

    // Já é URL absoluta: em página HTTPS, evita mixed-content forçando https.
    if (/^https?:\/\//i.test(p)) {
      if (window.location.protocol === "https:" && p.indexOf("http://") === 0) {
        return "https://" + p.slice(7);
      }
      return p;
    }

    // URL protocol-relative
    if (p.indexOf("//") === 0) {
      return window.location.protocol + p;
    }

    // Mantém chamadas same-origin como caminho relativo para respeitar protocolo atual.
    return p.charAt(0) === "/" ? p : "/" + p;
  }
  window.apiUrl = apiUrl;

  // Hardening extra: evita mixed-content mesmo se alguma chamada absoluta escapar.
  if (window.location.protocol === "https:" && typeof window.fetch === "function" && !window.__yuiFetchPatched) {
    var _origFetch = window.fetch.bind(window);
    window.fetch = function (input, init) {
      try {
        if (typeof input === "string") {
          if (input.indexOf("http://") === 0) input = "https://" + input.slice(7);
          else if (input.indexOf("//") === 0) input = "https:" + input;
        } else if (input && typeof input.url === "string" && input.url.indexOf("http://") === 0) {
          input = "https://" + input.url.slice(7);
        }
      } catch (e) {}
      return _origFetch(input, init);
    };
    window.__yuiFetchPatched = true;
  }

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
      parts.push('<div class="codeBlockWrap" data-lang="' + escapeHtml(lang) + '"><div class="codeBlockHeader"><span class="codeBlockLang">' + escapeHtml(lang) + '</span><button type="button" class="codeBlockCopy" title="Copiar código">Copiar código</button><button type="button" class="codeBlockToWorkspace" title="Enviar para o Workspace">Enviar para o Workspace</button><button type="button" class="codeBlockSaveProject" title="Salvar no projeto (sandbox) e atualizar árvore">Salvar no Projeto</button></div><pre><code class="language-' + escapeHtml(lang) + '">' + code + '</code></pre></div>');
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < rest.length) parts.push(escapeHtml(rest.slice(lastIndex)).replace(/\n/g, "<br>"));
    if (parts.length === 0) return escapeHtml(rest).replace(/\n/g, "<br>");
    return parts.join("");
  }

  function setupDownloadButton(link, url) {
    link.href = url;
    link.innerText = "⬇️ Baixar Projeto";
    link.className = "download-btn btn-download";
    link.setAttribute("download", url.split("/").pop() || "projeto.zip");
    link.addEventListener("click", function (e) {
      e.preventDefault();
      fetch(apiUrl(url)).then(function (r) {
        if (!r.ok) throw new Error(" ainda gerando");
        return r.blob();
      }).then(function (blob) {
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = url.split("/").pop() || "projeto.zip";
        a.click();
        URL.revokeObjectURL(a.href);
      }).catch(function () {
        if (link.getAttribute("data-ready") === "1") {
          window.open(url, "_blank");
        } else {
          alert("ZIP ainda gerando. Clique novamente em alguns segundos.");
        }
      });
    });
    var pollCount = 0;
    var pollInterval = setInterval(function () {
      pollCount++;
      if (pollCount > 30) { clearInterval(pollInterval); return; }
      fetch(apiUrl("/api/system/pending_downloads")).then(function (r) { return r.json(); }).then(function (data) {
        if (data.ok && (data.urls || []).indexOf(url) >= 0) {
          clearInterval(pollInterval);
          link.setAttribute("data-ready", "1");
          link.innerText = "✓ Baixar Projeto";
        }
      }).catch(function () {});
    }, 2000);
  }


  function tryAttachPendingDownloadButton(container, rawText) {
    if (!container) return;
    if (container.querySelector(".download-btn, .btn-download")) return;
    var text = (rawText || "").toLowerCase();
    if (text.indexOf("baixar projeto") < 0 && text.indexOf("compact") < 0 && text.indexOf("download") < 0) return;

    var link = document.createElement("a");
    link.href = "#";
    link.innerText = "⏳ Preparando download...";
    link.className = "download-btn btn-download";
    link.style.opacity = "0.8";
    link.style.pointerEvents = "none";
    container.appendChild(link);

    var tries = 0;
    var poll = setInterval(function () {
      tries++;
      if (tries > 30) {
        clearInterval(poll);
        link.innerText = "⚠️ ZIP não ficou pronto. Tente compactar novamente.";
        return;
      }
      fetch(apiUrl("/api/system/pending_downloads"))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var urls = (data && data.ok && data.urls) ? data.urls : [];
          if (!urls.length) return;
          var url = urls[urls.length - 1];
          clearInterval(poll);
          link.style.opacity = "";
          link.style.pointerEvents = "";
          setupDownloadButton(link, url);
          link.setAttribute("data-ready", "1");
          link.innerText = "✓ Baixar Projeto";
        })
        .catch(function () {});
    }, 2000);
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
    setupDownloadButton(link, url);
    container.appendChild(link);
  }

  function parseMultiWriteActions(text) {
    if (!text || typeof text !== "string") return [];
    var actions = [];
    var re = /\[(CREATE_FILE|UPDATE_FILE|DELETE_FILE):\s*([^\]]+)\]\s*(?:\n```\w*\n([\s\S]*?)```)?/g;
    var m;
    while ((m = re.exec(text)) !== null) {
      var action = m[1].toLowerCase().replace("_file", "");
      var path = m[2].trim().replace(/^\/+/, "").replace(/\\/g, "/");
      var content = (m[3] || "").trim();
      if (path && path.indexOf("..") < 0) {
        actions.push({ action: action, path: path, content: content });
      }
    }
    return actions;
  }

  function showWorkspaceProgress(show, percent, label) {
    var bar = document.getElementById("workspaceProgressBar");
    var fill = document.getElementById("workspaceProgressFill");
    var lbl = document.getElementById("workspaceProgressLabel");
    if (!bar) return;
    bar.style.display = show ? "block" : "none";
    if (fill) fill.style.width = (percent || 0) + "%";
    if (lbl) lbl.textContent = label || "Sincronizando Projeto...";
  }

  function applyMultiWriteActions(actions, msgDiv) {
    if (!actions || actions.length === 0) return;
    if (actions.length > 3) {
      var fileList = actions.map(function (a) { return a.path; }).join(", ");
      if (!confirm("Esta alteração afetará " + actions.length + " arquivos:\n\n" + fileList + "\n\nDeseja aplicar?")) return;
    }
    showWorkspaceProgress(true, 0, "Sincronizando Projeto...");
    var payload = { actions: actions.map(function (a) { return { action: a.action, path: a.path, content: a.content || "" }; }) };
    fetch(apiUrl("/api/sandbox/multi-save"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          showWorkspaceProgress(false);
          if (data.lint_errors && data.lint_errors.length) {
            alert("Erros de sintaxe:\n\n" + data.lint_errors.join("\n"));
          } else {
            alert("Erro: " + (data.error || "desconhecido"));
          }
          return;
        }
        showWorkspaceProgress(true, 100, "Concluído!");
        setTimeout(function () { showWorkspaceProgress(false); }, 800);
        if (window.addFileToWorkspace) {
          (data.saved || []).forEach(function (path) {
            var act = actions.find(function (a) { return a.path === path; });
            if (act && act.content) window.addFileToWorkspace(path, act.content);
          });
          (data.deleted || []).forEach(function (path) {
            if (window.removeFileFromWorkspace) window.removeFileFromWorkspace(path);
          });
        }
        if (msgDiv) {
          var btn = msgDiv.querySelector(".msgMultiWriteApply");
          if (btn) { btn.textContent = "✓ Aplicado"; btn.disabled = true; }
        }
      })
      .catch(function (e) {
        showWorkspaceProgress(false);
        alert("Erro ao sincronizar: " + (e.message || "Erro de rede"));
      });
  }

  function addTaskFromText(text) {
    if (!text || typeof text !== "string") return;
    var lines = text.split("\n");
    lines.forEach(function (ln) {
      var m = ln.match(/^\[TASK\]:\s*(.+)$/);
      if (m && m[1]) {
        addTask(m[1].trim());
      }
    });
  }

  function addTask(text) {
    if (!text || !text.trim()) return;
    var tasks = loadTasks();
    var t = text.trim();
    if (tasks.some(function (x) { return x.text === t; })) return;
    tasks.push({ id: Date.now().toString(), text: t, done: false });
    saveTasks(tasks);
    renderTasks();
  }

  function loadTasks() {
    try {
      var raw = localStorage.getItem("yui_tasks");
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  function saveTasks(tasks) {
    try { localStorage.setItem("yui_tasks", JSON.stringify(tasks)); } catch (e) {}
  }

  function toggleTask(id) {
    var tasks = loadTasks();
    var t = tasks.find(function (x) { return x.id === id; });
    if (t) { t.done = !t.done; saveTasks(tasks); renderTasks(); }
  }

  function removeTask(id) {
    var tasks = loadTasks().filter(function (x) { return x.id !== id; });
    saveTasks(tasks);
    renderTasks();
  }

  function renderTasks() {
    var list = document.getElementById("tasksList");
    var tasks = loadTasks();
    if (!list) return;
    list.innerHTML = "";
    tasks.forEach(function (t) {
      var li = document.createElement("li");
      if (t.done) li.classList.add("done");
      li.innerHTML = '<input type="checkbox" class="taskCheck" ' + (t.done ? "checked" : "") + ' data-id="' + escapeHtml(t.id) + '">' +
        '<span class="taskText">' + escapeHtml(t.text) + '</span>' +
        '<button type="button" class="taskDel" data-id="' + escapeHtml(t.id) + '">×</button>';
      var chk = li.querySelector(".taskCheck");
      var del = li.querySelector(".taskDel");
      if (chk) chk.addEventListener("change", function () { toggleTask(chk.dataset.id); });
      if (del) del.addEventListener("click", function () { removeTask(del.dataset.id); });
      list.appendChild(li);
    });
  }

  function initTasks() {
    renderTasks();
    var addBtn = document.getElementById("tasksAddBtn");
    var input = document.getElementById("tasksInput");
    if (addBtn && input) {
      addBtn.addEventListener("click", function () {
        input.style.display = input.style.display === "none" ? "block" : "none";
        if (input.style.display !== "none") input.focus();
      });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && input.value.trim()) {
          addTask(input.value.trim());
          input.value = "";
          input.style.display = "none";
        }
      });
    }
  }

  function finalizeAssistantBubble(bubble) {
    if (!bubble) return;
    var target = bubble.querySelector(".msgBubbleInner") || bubble;
    var fullText = bubble.textContent || "";
    addTaskFromText(fullText);
    var cleaned = fullText.replace(/\n?\[DOWNLOAD\]:\S+/, "").trim();
    cleaned = cleaned.replace(/\n?\[TASK\]:[^\n]*/g, "").trim();
    target.innerHTML = formatMarkdownToHtml(cleaned);
    attachCodeBlockCopyButtons(target);
    initDownloadButtons(target, fullText);
    if (typeof window.hljs !== "undefined") {
      target.querySelectorAll("pre code").forEach(function (el) {
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
    container.querySelectorAll(".codeBlockSaveProject").forEach(function (btn) {
      if (btn._saveProjectAttached) return;
      btn._saveProjectAttached = true;
      btn.addEventListener("click", function () {
        var wrap = btn.closest(".codeBlockWrap");
        if (!wrap) return;
        var codeEl = wrap.querySelector("code");
        var lang = wrap.getAttribute("data-lang") || "text";
        if (!codeEl) return;
        var code = codeEl.textContent || "";
        var extMap = { py: "py", python: "py", js: "js", javascript: "js", ts: "ts", typescript: "ts", html: "html", css: "css", json: "json", md: "md", markdown: "md" };
        var ext = extMap[(lang || "text").toLowerCase()] || "txt";
        var defaultName = (ext === "py" ? "main" : ext === "js" ? "index" : "file") + "." + ext;
        var path = prompt("Caminho do arquivo no projeto:", defaultName);
        if (!path || !path.trim()) return;
        path = path.replace(/^\/+/, "").replace(/\\/g, "/").trim();
        if (path.indexOf("..") >= 0) { alert("Caminho inválido."); return; }
        var orig = btn.textContent;
        btn.textContent = "Salvando...";
        btn.disabled = true;
        fetch(apiUrl("/api/sandbox/save"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files: [{ path: path, content: code }] }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.ok && window.addFileToWorkspace) {
              window.addFileToWorkspace(path, code);
              if (window.updateEditor) window.updateEditor(code, window.getLangFromPath ? window.getLangFromPath(path) : lang);
            }
          })
          .catch(function () {})
          .finally(function () {
            btn.textContent = orig;
            btn.disabled = false;
          });
      });
    });
  }

  function openPreview(url, title) {
    if (!previewPanel || !previewFrame) return;
    var src = url || "about:blank";
    if (src !== "about:blank" && src.indexOf("http") !== 0) {
      var origin = window.location.origin || (window.location.protocol + "//" + window.location.host);
      src = origin + (src.indexOf("/") === 0 ? src : "/" + src);
    }
    previewFrame.src = src;
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
  window.getWorkspaceOpen = function () { return workspaceOpen; };
  function getWorkspacePref() {
    try {
      var v = localStorage.getItem("yui_workspace_open");
      return v === null ? true : v === "true";
    } catch (e) { return true; }
  }
  var workspaceEverInitialized = false;
  function setWorkspacePref(open) {
    try { localStorage.setItem("yui_workspace_open", String(open)); } catch (e) {}
  }
  function toggleWorkspace() {
    workspaceOpen = !workspaceOpen;
    setWorkspacePref(workspaceOpen);
    try {
      fetch(apiUrl("/api/system/events"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: "workspace_toggled", data: { open: workspaceOpen } })
      }).catch(function () {});
    } catch (e) {}
    if (workspaceOpen && !workspaceEverInitialized) {
      workspaceEverInitialized = true;
      if (window.loadWorkspaceLibs) {
        window.loadWorkspaceLibs(function () {
          if (window.initYuiWorkspace) window.initYuiWorkspace();
        });
      } else if (window.initYuiWorkspace) {
        window.initYuiWorkspace();
      }
    }
    var mainSplit = document.querySelector(".mainSplit");
    var btn = document.getElementById("toggleWorkspace");
    if (mainSplit) {
      mainSplit.classList.toggle("workspaceCollapsed", !workspaceOpen);
      mainSplit.classList.toggle("editor-hidden", !workspaceOpen);
    }
    if (btn) btn.classList.toggle("workspaceClosed", !workspaceOpen);
    var chatAreaEl = document.getElementById("chatArea");
    if (chatAreaEl) {
      if (workspaceOpen && window.restoreChatWidth) window.restoreChatWidth();
      else if (!workspaceOpen && window.clearChatWidth) window.clearChatWidth();
    }
    if (workspaceOpen) setTimeout(function () { window.dispatchEvent(new Event("resize")); }, 420);
  }
  function initMainSplitResizer() {
    var resizer = document.getElementById("mainSplitResizer");
    var chatArea = document.getElementById("chatArea");
    var workspacePanel = document.getElementById("workspacePanel");
    var mainSplit = document.querySelector(".mainSplit");
    if (!resizer || !chatArea || !workspacePanel || !mainSplit) return;
    var STORAGE_KEY = "yui_chat_width";
    var MIN_CHAT = 280;
    var MAX_CHAT_PERCENT = 0.5;
    function getMaxChatWidth() {
      return Math.floor(mainSplit.offsetWidth * MAX_CHAT_PERCENT);
    }
    function applyChatWidth(w) {
      var maxW = getMaxChatWidth();
      w = Math.max(MIN_CHAT, Math.min(maxW, w));
      chatArea.style.flex = "0 0 " + w + "px";
      chatArea.style.minWidth = w + "px";
      chatArea.style.maxWidth = w + "px";
      try { localStorage.setItem(STORAGE_KEY, String(w)); } catch (e) {}
    }
    function clearChatWidth() {
      chatArea.style.flex = "";
      chatArea.style.minWidth = "";
      chatArea.style.maxWidth = "";
    }
    window.restoreChatWidth = function () {
      try {
        var saved = parseInt(localStorage.getItem(STORAGE_KEY), 10);
        if (saved && saved >= MIN_CHAT) applyChatWidth(saved);
        else clearChatWidth();
      } catch (e) { clearChatWidth(); }
    };
    window.clearChatWidth = clearChatWidth;
    try {
      var saved = parseInt(localStorage.getItem(STORAGE_KEY), 10);
      if (saved && saved >= MIN_CHAT) applyChatWidth(saved);
    } catch (e) {}
    var dragging = false;
    var startX = 0;
    var startWidth = 0;
    resizer.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      if (mainSplit.classList.contains("workspaceCollapsed") || mainSplit.classList.contains("editor-hidden")) return;
      dragging = true;
      resizer.classList.add("resizing");
      startX = e.clientX;
      startWidth = chatArea.offsetWidth;
      e.preventDefault();
    });
    document.addEventListener("mousemove", function (e) {
      if (!dragging) return;
      var dx = e.clientX - startX;
      applyChatWidth(startWidth + dx);
    });
    document.addEventListener("mouseup", function () {
      if (dragging) {
        dragging = false;
        resizer.classList.remove("resizing");
      }
    });
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
    var chatAreaEl = document.getElementById("chatArea");
    if (chatAreaEl && window.restoreChatWidth && window.clearChatWidth) {
      if (workspaceOpen) window.restoreChatWidth();
      else window.clearChatWidth();
    }
    if (btn) btn.addEventListener("click", toggleWorkspace);
    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.key === "l") {
        e.preventDefault();
        toggleWorkspace();
      }
    });
    if (workspaceOpen) {
      workspaceEverInitialized = true;
      if (window.loadWorkspaceLibs) {
        window.loadWorkspaceLibs(function () {
          if (window.initYuiWorkspace) window.initYuiWorkspace();
        });
      } else if (window.initYuiWorkspace) {
        window.initYuiWorkspace();
      }
    }
  }

  function showApp() {
    if (loginScreen) loginScreen.style.display = "none";
    if (appScreen) appScreen.style.display = "flex";
    initMainSplitResizer();
    initWorkspaceToggle();
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

  var deployYuiBtn = document.getElementById("btnDeployYui");
  if (deployYuiBtn) {
    deployYuiBtn.addEventListener("click", function () {
      var msg = prompt("Mensagem do commit:", "Deploy via Yui");
      if (msg === null) return;
      deployYuiBtn.disabled = true;
      deployYuiBtn.classList.add("loading");
      deployYuiBtn.textContent = "Enviando...";
      fetch(apiUrl("/api/sandbox/deploy"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg || "Deploy via Yui" }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) alert(data.message || "Deploy concluído!");
          else alert("Erro: " + (data.error || "desconhecido"));
        })
        .catch(function (e) { alert("Erro de rede: " + (e.message || "")); })
        .finally(function () {
          deployYuiBtn.disabled = false;
          deployYuiBtn.classList.remove("loading");
          deployYuiBtn.textContent = "Deploy via Yui";
        });
    });
  }

  var clearChatBtn = document.getElementById("clearChat");
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", async function () {
      try {
        var body = {};
        if (user && user.id) body.user_id = user.id;
        await fetch(apiUrl("/clear_chat"), {
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
      var res = await fetch(apiUrl("/api/user/profile/get"), {
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
        await fetch(apiUrl("/api/user/profile"), {
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
      var res = await fetch(apiUrl("/api/chats/" + encodeURIComponent(user.id)));
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

  function renderChatSuggestions() {
    if (!chat || !chatAtual || !user) return;
    var suggestions = [
      "Explique conceitos de programação de forma simples",
      "Crie um projeto Flask com API REST",
      "Ajude-me a debugar um erro no meu código",
      "Gere uma landing page moderna em HTML/CSS",
      "Como implementar autenticação em uma aplicação web?",
      "Escreva um script Python para automatizar tarefas",
      "Sugira melhorias para a arquitetura do meu projeto",
      "Traduza este código para outra linguagem"
    ];
    var wrap = document.createElement("div");
    wrap.className = "chatSuggestionsWrap";
    var title = document.createElement("div");
    title.className = "chatSuggestionsTitle";
    title.textContent = "Como posso ajudar hoje?";
    wrap.appendChild(title);
    var grid = document.createElement("div");
    grid.className = "chatSuggestionsGrid";
    suggestions.forEach(function (s) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chatSuggestionBtn";
      btn.textContent = s;
      btn.addEventListener("click", function () {
        msgInput.value = s;
        msgInput.focus();
        wrap.remove();
      });
      grid.appendChild(btn);
    });
    wrap.appendChild(grid);
    chat.appendChild(wrap);
  }

  function renderMensagensNoChat(msgs) {
    if (!chat) return;
    chat.innerHTML = "";
    if (!Array.isArray(msgs) || msgs.length === 0) {
      if (chatAtual && user) renderChatSuggestions();
      chat.scrollTop = 0;
      return;
    }
    msgs.forEach(function (m, idx) {
      var div = document.createElement("div");
      div.className = "msgBubble " + (m.role === "user" ? "user" : "assistant");
      if (m.id) div.dataset.messageId = m.id;
      var avatar = document.createElement("div");
      avatar.className = "msgAvatar " + (m.role === "user" ? "msgAvatarUser" : "msgAvatarAssistant");
      avatar.innerHTML = m.role === "user" ? "👤" : "🤖";
      avatar.title = m.role === "user" ? "Você" : "Yui";
      div.appendChild(avatar);
      var contentWrap = document.createElement("div");
      contentWrap.className = "msgBubbleInner";

      var prevUserMsg = null;
      if (m.role === "assistant" && idx > 0) {
        for (var i = idx - 1; i >= 0; i--) {
          if (msgs[i].role === "user") {
            prevUserMsg = (msgs[i].content || "").trim();
            break;
          }
        }
      }

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

        var btnCopy = document.createElement("button");
        btnCopy.className = "msgActionBtn";
        btnCopy.type = "button";
        btnCopy.textContent = "📋";
        btnCopy.title = "Copiar mensagem";
        btnCopy.addEventListener("click", function (e) {
          e.stopPropagation();
          var txt = (m.content || "").trim();
          if (txt && navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(txt).then(function () {
              var old = btnCopy.textContent;
              btnCopy.textContent = "✓";
              setTimeout(function () { btnCopy.textContent = old; }, 1500);
            });
          }
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

        if (m.role === "assistant" && prevUserMsg) {
          var btnRegen = document.createElement("button");
          btnRegen.className = "msgActionBtn";
          btnRegen.type = "button";
          btnRegen.textContent = "🔄";
          btnRegen.title = "Regenerar resposta";
          btnRegen.addEventListener("click", function (e) {
            e.stopPropagation();
            regenerarResposta(div, prevUserMsg);
          });
          actions.appendChild(btnRegen);
        }
        actions.appendChild(btnReply);
        actions.appendChild(btnImprove);
        actions.appendChild(btnCopy);
        actions.appendChild(btnDelete);
        contentWrap.appendChild(actions);
      }

      var content = document.createElement("div");
      content.className = "msgContent";
      var raw = m.content || "";
      var previewUrl = null;
      var downloadUrl = null;
      if (m.role === "assistant") {
        addTaskFromText(raw);
        var linhas = raw.split("\n");
        var filtradas = [];
        linhas.forEach(function (ln) {
          if (ln.indexOf("[PREVIEW_URL]:") === 0) {
            previewUrl = ln.replace("[PREVIEW_URL]:", "").trim();
          } else if (ln.indexOf("[DOWNLOAD]:") === 0) {
            downloadUrl = ln.replace("[DOWNLOAD]:", "").trim();
          } else if (ln.indexOf("[TASK]:") === 0) {
            /* já extraído em addTaskFromText */
          } else {
            filtradas.push(ln);
          }
        });
        raw = filtradas.join("\n");
      }
      if (m.role === "assistant" && raw) {
        content.innerHTML = formatMarkdownToHtml(raw);
        attachCodeBlockCopyButtons(content);
        var multiWriteActions = parseMultiWriteActions(m.content || raw);
        if (multiWriteActions.length > 0) {
          var btnApply = document.createElement("button");
          btnApply.type = "button";
          btnApply.className = "msgMultiWriteApply";
          btnApply.textContent = "Aplicar alterações (" + multiWriteActions.length + " arquivos)";
          btnApply.addEventListener("click", function () {
            applyMultiWriteActions(multiWriteActions, div);
          });
          content.appendChild(btnApply);
        }
        var lessonError = "";
        try { lessonError = sessionStorage.getItem("yui_lesson_error") || ""; } catch (e) {}
        if (lessonError && (raw.indexOf("```") >= 0 || multiWriteActions.length > 0)) {
          var btnLesson = document.createElement("button");
          btnLesson.type = "button";
          btnLesson.className = "msgLessonBtn";
          btnLesson.textContent = "Registrar em Lessons Learned";
          btnLesson.title = "Gravar esta correção em .yui_lessons.md para não repetir";
          btnLesson.addEventListener("click", function () {
            var correction = m.content || "";
            if (multiWriteActions.length > 0) {
              correction = multiWriteActions.map(function (a) { return "[" + a.action + "] " + a.path + (a.content ? "\n" + a.content.slice(0, 300) : ""); }).join("\n\n");
            } else {
              var mm = (m.content || "").match(/```[\s\S]*?```/);
              correction = mm ? mm[0] : correction.slice(0, 500);
            }
            var ctx = "";
            try { ctx = sessionStorage.getItem("yui_lesson_context") || ""; } catch (e) {}
            fetch(apiUrl("/api/sandbox/lessons"), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ error: lessonError, correction: correction.slice(0, 2000), context: ctx }),
            })
              .then(function (r) { return r.json(); })
              .then(function (data) {
                if (data.ok) {
                  btnLesson.textContent = "✓ Registrado";
                  btnLesson.disabled = true;
                  try { sessionStorage.removeItem("yui_lesson_error"); sessionStorage.removeItem("yui_lesson_context"); } catch (e) {}
                } else { alert("Erro: " + (data.error || "")); }
              })
              .catch(function () { alert("Erro ao registrar"); });
          });
          content.appendChild(btnLesson);
        }
      } else {
        content.textContent = raw;
      }
      contentWrap.appendChild(content);

      if (downloadUrl) {
        var link = document.createElement("a");
        setupDownloadButton(link, downloadUrl);
        contentWrap.appendChild(link);
      } else if (m.role === "assistant") {
        tryAttachPendingDownloadButton(contentWrap, m.content || raw);
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
        contentWrap.appendChild(btnPrev);
      }
      div.appendChild(contentWrap);
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
      var url = apiUrl("/api/messages/" + encodeURIComponent(loadingFor) + "?user_id=" + encodeURIComponent(user.id));
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
      fetchMission();
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
      var res = await fetch(apiUrl("/api/chat/new"), {
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
      var res = await fetch(apiUrl("/api/chat/delete"), {
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
      fetch(apiUrl("/api/message/edit"), {
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
    fetch(apiUrl("/api/message/edit"), {
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
    fetch(apiUrl("/api/message/delete"), {
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

  function regenerarResposta(bubble, prevUserMsg) {
    if (!chatAtual || !user || !prevUserMsg) return;
    var messageId = bubble && bubble.dataset ? bubble.dataset.messageId : null;
    var btnEnviar = document.getElementById("btnEnviar");
    bubble.remove();
    if (messageId) {
      fetch(apiUrl("/api/message/delete"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, user_id: user.id })
      }).catch(function () {});
    }
    delete messagesCache[chatAtual];
    var assistantBubble = document.createElement("div");
    assistantBubble.className = "msgBubble assistant";
    assistantBubble.setAttribute("data-status", "sending");
    var avatar = document.createElement("div");
    avatar.className = "msgAvatar msgAvatarAssistant";
    avatar.innerHTML = "🤖";
    assistantBubble.appendChild(avatar);
    var inner = document.createElement("div");
    inner.className = "msgBubbleInner";
    var statusLine = document.createElement("div");
    statusLine.className = "assistantStatus";
    statusLine.textContent = "🧠 Pensando...";
    var cursor = document.createElement("span");
    cursor.className = "cursorStream";
    inner.appendChild(statusLine);
    inner.appendChild(cursor);
    assistantBubble.appendChild(inner);
    chat.appendChild(assistantBubble);
    chat.scrollTop = chat.scrollHeight;
    if (btnEnviar) btnEnviar.disabled = true;
    var body = { chat_id: chatAtual, user_id: user.id, message: prevUserMsg, model: getCurrentModel() };
    var ctx = window.getWorkspaceContext && window.getWorkspaceContext();
    if (ctx) { body.active_files = ctx.active_files || []; body.console_errors = ctx.console_errors || []; }
    body.workspace_open = window.getWorkspaceOpen ? window.getWorkspaceOpen() : false;
    fetch(apiUrl("/api/chat/stream"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok || !r.body) throw new Error("Stream failed"); return r.body.getReader(); })
      .then(function (reader) {
        var decoder = new TextDecoder();
        var buffer = "";
        function read() {
          return reader.read().then(function (result) {
            if (result.done) {
              if (cursor && cursor.parentNode) cursor.remove();
              assistantBubble.setAttribute("data-status", "sent");
              finalizeAssistantBubble(assistantBubble);
              if (btnEnviar) btnEnviar.disabled = false;
              fetchTelemetry();
              fetchCognitive();
              fetchMission();
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            var events = buffer.split("\n\n");
            buffer = events.pop() || "";
            events.forEach(function (event) {
              var idx = event.indexOf("data: ");
              if (idx === -1) return;
              try {
                var payload = event.slice(idx + 6).trim();
                if (!payload) return;
                var chunk = JSON.parse(payload);
                if (typeof chunk === "string" && chunk.indexOf("__STATUS__:") === 0) {
                  var state = chunk.slice("__STATUS__:".length);
                  if (state === "done") {
                    statusLine.remove();
                    if (cursor && cursor.parentNode) cursor.remove();
                    assistantBubble.setAttribute("data-status", "sent");
                    finalizeAssistantBubble(assistantBubble);
                  } else if (state === "thinking") {
                    statusLine.textContent = "🧠 Pensando...";
                  } else {
                    statusLine.textContent = state.slice("executing_tools:".length) || "🔧 Executando...";
                  }
                  return;
                }
                if (typeof chunk === "string" && chunk.indexOf("__BUDGET_CONFIRM__:") === 0) return;
                assistantBubble.setAttribute("data-status", "streaming");
                var textNode = document.createTextNode(chunk);
                (cursor.parentNode || assistantBubble).insertBefore(textNode, cursor);
              } catch (e) {}
            });
            chat.scrollTop = chat.scrollHeight;
            return read();
          });
        }
        return read();
      })
      .catch(function () {
        if (cursor && cursor.parentNode) cursor.remove();
        assistantBubble.setAttribute("data-status", "error");
        var errTarget = assistantBubble.querySelector(".msgBubbleInner") || assistantBubble;
        errTarget.textContent = "Erro ao regenerar. Tente novamente.";
        if (btnEnviar) btnEnviar.disabled = false;
      });
  }

  var refreshBtn = document.getElementById("refreshPage");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      try {
        refreshBtn.disabled = true;
        refreshBtn.textContent = "Atualizando...";
      } catch (e) {}
      window.location.reload();
    });
  }

  document.getElementById("novoChat").addEventListener("click", async function () {
    if (!user || !user.id) return;
    var id = await criarNovoChat();
    if (id) {
      setChatAtual(id, "Novo chat");
      carregarChats(true);
      chat.innerHTML = "";
      renderChatSuggestions();
    } else {
      chat.innerHTML = "<div class=\"chatVazio\">Erro ao criar chat. Tente de novo.</div>";
    }
  });

  function isNovoChatTitulo(titulo) {
    return (titulo || "").toLowerCase() === "novo chat";
  }

  function atualizarTituloChat(chatId, firstMessage) {
    fetch(apiUrl("/api/chat/title"), {
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
      var userAvatar = document.createElement("div");
      userAvatar.className = "msgAvatar msgAvatarUser";
      userAvatar.innerHTML = "👤";
      userAvatar.title = "Você";
      userBubble.appendChild(userAvatar);
      var userContent = document.createElement("div");
      userContent.className = "msgBubbleInner";
      userContent.textContent = texto || (temArquivo ? "📎 Arquivo enviado" : "");
      if (temArquivo && pendingFileName) {
        var tag = document.createElement("div");
        tag.className = "fileTag";
        tag.textContent = "📎 " + pendingFileName;
        userContent.appendChild(tag);
      }
      userBubble.appendChild(userContent);
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
        fetch(apiUrl("/api/upload"), { method: "POST", body: formData })
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

        fetch(apiUrl("/api/send"), {
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
            fetchCognitive();
            fetchMission();
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
        var avatar = document.createElement("div");
        avatar.className = "msgAvatar msgAvatarAssistant";
        avatar.innerHTML = "🤖";
        avatar.title = "Yui";
        assistantBubble.appendChild(avatar);
        var inner = document.createElement("div");
        inner.className = "msgBubbleInner";
        var statusLine = document.createElement("div");
        statusLine.className = "assistantStatus";
        statusLine.textContent = "🧠 Pensando...";
        var cursor = document.createElement("span");
        cursor.className = "cursorStream";
        inner.appendChild(statusLine);
        inner.appendChild(cursor);
        assistantBubble.appendChild(inner);
        chat.appendChild(assistantBubble);
        chat.scrollTop = chat.scrollHeight;

        if (btnEnviar) btnEnviar.disabled = true;

        function runStreamFetch(cId, txt, confirmHighCost, aBubble, sLine, cur, btn) {
          var body = { chat_id: cId, user_id: user.id, message: txt, model: getCurrentModel() };
          if (confirmHighCost) body.confirm_high_cost = true;
          var ctx = window.getWorkspaceContext && window.getWorkspaceContext();
          if (ctx) {
            body.active_files = ctx.active_files || [];
            body.console_errors = ctx.console_errors || [];
          }
          body.workspace_open = window.getWorkspaceOpen ? window.getWorkspaceOpen() : false;
          fetch(apiUrl("/api/chat/stream"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
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
                  if (cur && cur.parentNode) cur.remove();
                  aBubble.setAttribute("data-status", "sent");
                  finalizeAssistantBubble(aBubble);
                  if (btn) btn.disabled = false;
                  if (isNovoChatTitulo(currentChatTitulo)) {
                    atualizarTituloChat(cId, txt);
                  }
                  fetchTelemetry();
                  fetchCognitive();
                  fetchMission();
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
                        if (!sLine) return;
                        var state = chunk.slice("__STATUS__:".length);
                        if (state === "thinking") {
                          sLine.textContent = "🧠 Pensando...";
                          aBubble.setAttribute("data-status", "sending");
                        } else if (state === "planejando") {
                          sLine.textContent = "⚙️ Planejando...";
                          aBubble.setAttribute("data-status", "streaming");
                        } else if (state === "analyzing_code") {
                          sLine.textContent = "🔎 Analisando código...";
                          aBubble.setAttribute("data-status", "streaming");
                        } else if (state.indexOf("executing_tools:") === 0) {
                          sLine.textContent = state.slice("executing_tools:".length) || "🔧 Executando ferramentas...";
                          aBubble.setAttribute("data-status", "streaming");
                        } else if (state === "executing_tools") {
                          sLine.textContent = "🔧 Executando ferramentas...";
                          aBubble.setAttribute("data-status", "streaming");
                        } else if (state === "done") {
                          sLine.remove();
                          if (cur && cur.parentNode) cur.remove();
                          aBubble.setAttribute("data-status", "sent");
                          finalizeAssistantBubble(aBubble);
                        }
                        return;
                      }
                      if (typeof chunk === "string" && chunk.indexOf("__BUDGET_CONFIRM__:") === 0) {
                        var parts = chunk.split(":");
                        var costVal = parts[1] || "0";
                        var msg = parts.slice(2).join(":").trim() || ("Custo estimado R$ " + costVal + ". Deseja continuar?");
                        if (sLine) sLine.remove();
                        if (cur && cur.parentNode) cur.remove();
                        var innerEl = aBubble.querySelector(".msgBubbleInner") || aBubble;
                        innerEl.innerHTML = "<div class=\"assistantStatus\">" + escapeHtml(msg) + "</div><button type=\"button\" class=\"msgBudgetConfirm\">Sim, continuar</button>";
                        aBubble.setAttribute("data-status", "budget_confirm");
                        if (btn) btn.disabled = false;
                        var confirmBtn = aBubble.querySelector(".msgBudgetConfirm");
                        if (confirmBtn) {
                          confirmBtn.addEventListener("click", function () {
                            innerEl.innerHTML = "";
                            var newStatus = document.createElement("div");
                            newStatus.className = "assistantStatus";
                            newStatus.textContent = "🧠 Pensando...";
                            var newCursor = document.createElement("span");
                            newCursor.className = "cursorStream";
                            innerEl.appendChild(newStatus);
                            innerEl.appendChild(newCursor);
                            aBubble.setAttribute("data-status", "sending");
                            if (btn) btn.disabled = true;
                            runStreamFetch(cId, txt, true, aBubble, newStatus, newCursor, btn);
                          });
                        }
                        return;
                      }
                      aBubble.setAttribute("data-status", "streaming");
                      var textNode = document.createTextNode(chunk);
                      (cur.parentNode || aBubble).insertBefore(textNode, cur);
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
            if (cur && cur.parentNode) cur.remove();
            aBubble.setAttribute("data-status", "error");
            var errTarget = aBubble.querySelector(".msgBubbleInner") || aBubble;
            errTarget.textContent = "Erro de rede ou streaming não disponível. Tente novamente.";
            if (btn) btn.disabled = false;
            chat.scrollTop = chat.scrollHeight;
          });
        }
        runStreamFetch(chatId, texto, false, assistantBubble, statusLine, cursor, btnEnviar);
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
    if (saved === "yui" || saved === "heathcliff" || saved === "auto") {
      modelSwitcher.value = saved;
      applyModelVisual(saved);
    }
  }

  initTasks();

  (function initSidebarCollapse() {
    var SIDEBAR_STORAGE_KEY = "yui_sidebar_collapsed";
    var sidebar = document.getElementById("sidebar");
    var toggleBtn = document.getElementById("sidebarToggle");
    if (sidebar && toggleBtn) {
      var collapsed = localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
      if (collapsed) sidebar.classList.add("collapsed");
      toggleBtn.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
        localStorage.setItem(SIDEBAR_STORAGE_KEY, sidebar.classList.contains("collapsed"));
      });
    }
  })();

  (function initSidebarTabs() {
    var tabs = document.querySelectorAll(".sidebarTab[data-sidebar-tab]");
    var contents = document.querySelectorAll(".sidebarTabContent");
    function switchToTab(tab) {
      var key = tab.getAttribute("data-sidebar-tab") || "";
      var targetId = "sidebarTab" + key.charAt(0).toUpperCase() + key.slice(1);
      tabs.forEach(function (t) { t.classList.remove("active"); });
      contents.forEach(function (c) {
        c.style.display = "none";
        c.classList.remove("active");
      });
      tab.classList.add("active");
      var target = document.getElementById(targetId);
      if (target) {
        target.style.display = "flex";
        target.classList.add("active");
      }
      localStorage.setItem("yui_sidebar_tab", key);
    }
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () { switchToTab(tab); });
    });
    var savedTab = localStorage.getItem("yui_sidebar_tab") || "tarefas";
    var savedTabEl = document.querySelector('.sidebarTab[data-sidebar-tab="' + savedTab + '"]');
    if (savedTabEl && savedTab !== "tarefas") switchToTab(savedTabEl);
  })();

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
    fetch(apiUrl("/api/system/health"))
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
        document.body.classList.toggle("economy-mode", ram > 70);
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
    fetch(apiUrl("/api/system/telemetry"))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var costEl = document.getElementById("telemetryCost");
        var reqEl = document.getElementById("telemetryRequests");
        var lastEl = document.getElementById("telemetryLastResponse");
        var tokensEl = document.getElementById("telemetryTokens");
        var diskEl = document.getElementById("telemetryDiskWrites");
        if (costEl) costEl.textContent = (data.cost_estimate != null ? "R$ " + data.cost_estimate.toFixed(2) : "—");
        if (reqEl) reqEl.textContent = (data.requests != null ? data.requests : "—");
        if (lastEl) lastEl.textContent = (data.last_response_cost != null && data.last_response_cost > 0 ? "R$ " + data.last_response_cost.toFixed(4) : "—");
        if (tokensEl) {
          var t = data.last_response_tokens;
          tokensEl.textContent = (t && (t.prompt != null || t.completion != null)) ? (t.prompt || 0) + " / " + (t.completion || 0) : "—";
        }
        if (diskEl) diskEl.textContent = (data.disk_writes != null && data.disk_writes > 0) ? (data.disk_writes + " (R$ " + (data.disk_write_cost_brl || 0).toFixed(4) + ")") : "—";
      })
      .catch(function () {
        var costEl = document.getElementById("telemetryCost");
        var reqEl = document.getElementById("telemetryRequests");
        var lastEl = document.getElementById("telemetryLastResponse");
        var tokensEl = document.getElementById("telemetryTokens");
        var diskEl = document.getElementById("telemetryDiskWrites");
        if (costEl) costEl.textContent = "—";
        if (reqEl) reqEl.textContent = "—";
        if (lastEl) lastEl.textContent = "—";
        if (tokensEl) tokensEl.textContent = "—";
        if (diskEl) diskEl.textContent = "—";
      });
  }

  function fetchCognitive() {
    fetch(apiUrl("/api/system/cognitive"))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var confEl = document.getElementById("cognitiveConfidence");
        var scoreEl = document.getElementById("cognitiveScore");
        var ramEl = document.getElementById("cognitiveRam");
        if (confEl) confEl.textContent = (data.planner_confidence != null ? data.planner_confidence + "%" : "—");
        if (scoreEl) scoreEl.textContent = data.last_action_score || "—";
        if (ramEl) ramEl.textContent = data.ram_impact || "—";
      })
      .catch(function () {
        var confEl = document.getElementById("cognitiveConfidence");
        var scoreEl = document.getElementById("cognitiveScore");
        var ramEl = document.getElementById("cognitiveRam");
        if (confEl) confEl.textContent = "—";
        if (scoreEl) scoreEl.textContent = "—";
        if (ramEl) ramEl.textContent = "—";
      });
  }

  function fetchSkills() {
    fetch(apiUrl("/api/system/skills"))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var ul = document.getElementById("skillsList");
        if (ul) {
          var skills = (data && data.skills) || [];
          if (skills.length === 0) {
            ul.innerHTML = "<li class=\"activityEmpty\">—</li>";
          } else {
            ul.innerHTML = skills.map(function (s) {
              return "<li class=\"skillItem\"><span class=\"skillCheck\">✔</span> " + (s.name || "—") + "</li>";
            }).join("");
          }
        }
      })
      .catch(function () {
        var ul = document.getElementById("skillsList");
        if (ul) ul.innerHTML = "<li class=\"activityEmpty\">—</li>";
      });
  }

  function fetchActivity() {
    fetch(apiUrl("/api/system/observability"))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var ul = document.getElementById("activityList");
        if (ul) {
          var items = (data && data.activity) || [];
          if (items.length === 0) {
            ul.innerHTML = "<li class=\"activityEmpty\">—</li>";
          } else {
            var sym = { graph: "⚡", task: "⏳", governor: "🛡️", event: "📡", routing: "🧠" };
            ul.innerHTML = items.slice(0, 6).map(function (a) {
              var s = sym[a.kind] || "•";
              var txt = a.label + (a.detail ? " (" + a.detail + ")" : "");
              return "<li><span class=\"activityKind\">" + s + "</span> " + txt + "</li>";
            }).join("");
          }
        }
        var tlUl = document.getElementById("activityTimelineList");
        if (tlUl) {
          var timeline = (data && data.timeline) || [];
          if (timeline.length === 0) {
            tlUl.innerHTML = "<li class=\"activityEmpty\">—</li>";
          } else {
            var symMap = { done: "✓", failed: "✗", running: "⚡" };
            tlUl.innerHTML = timeline.slice(0, 8).map(function (t) {
              var s = symMap[t.status] || "○";
              var dur = t.duration_ms != null ? t.duration_ms + "ms" : (t.status === "running" ? "…" : "—");
              if (t.duration_ms != null && t.duration_ms >= 1000) {
                dur = (t.duration_ms / 1000).toFixed(1) + "s";
              }
              return "<li><span class=\"timelineSymbol\">" + s + "</span><span class=\"timelineName\">" + (t.name || "—") + "</span><span class=\"timelineDuration\">" + dur + "</span></li>";
            }).join("");
          }
        }
      })
      .catch(function () {
        var ul = document.getElementById("activityList");
        if (ul) ul.innerHTML = "<li class=\"activityEmpty\">—</li>";
        var tlUl = document.getElementById("activityTimelineList");
        if (tlUl) tlUl.innerHTML = "<li class=\"activityEmpty\">—</li>";
      });
  }

  function fetchMission() {
    if (!user || !user.id) return;
    var uid = encodeURIComponent(user.id);
    var cid = chatAtual ? encodeURIComponent(chatAtual) : "";
    var url = apiUrl("/api/missions/?user_id=" + uid + (cid ? "&chat_id=" + cid : ""));
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var panel = document.getElementById("missionPanel");
        var goalEl = document.getElementById("missionGoal");
        var fillEl = document.getElementById("missionProgressFill");
        var labelEl = document.getElementById("missionProgressLabel");
        var taskEl = document.getElementById("missionCurrentTask");
        if (!panel || !goalEl || !fillEl || !labelEl || !taskEl) return;
        var m = data && data.mission;
        if (!m || m.status !== "in_progress") {
          panel.style.display = "none";
          return;
        }
        panel.style.display = "block";
        goalEl.textContent = (m.project ? m.project + ": " : "") + (m.goal || "—");
        var pct = Math.round((m.progress || 0) * 100);
        fillEl.style.width = pct + "%";
        labelEl.textContent = pct + "%";
        taskEl.textContent = m.current_task || "";
        taskEl.style.display = m.current_task ? "block" : "none";
      })
      .catch(function () {
        var panel = document.getElementById("missionPanel");
        if (panel) panel.style.display = "none";
      });
  }

  var systemPollingStarted = false;
  function isChatActive() {
    var app = document.getElementById("appScreen");
    return app && app.offsetParent !== null;
  }
  function startSystemPolling() {
    if (systemPollingStarted) return;
    systemPollingStarted = true;
    fetchSystemHealth();
    fetchTelemetry();
    fetchCognitive();
    fetchSkills();
    fetchActivity();
    fetchMission();
    setInterval(function () {
      if (isChatActive()) {
        fetchSystemHealth();
        fetchTelemetry();
        fetchSkills();
        fetchCognitive();
        fetchActivity();
        fetchMission();
      }
    }, 30000);
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
