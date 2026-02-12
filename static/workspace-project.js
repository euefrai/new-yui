/**
 * YUI Workspace — Editor de projetos com File Tree
 * Importar pasta, trocar arquivos, exportar ZIP, Alimentar Yui
 */
(function () {
  "use strict";

  var projectFiles = {};
  var originalFileContents = {};
  var projectTree = [];
  var currentFilePath = null;
  var projectName = "projeto";
  var lastConsoleError = null;

  var ICON_FOLDER = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
  var ICON_FILE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
  var ICON_ARROW_RIGHT = '<svg class="folderArrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>';
  var ICON_ARROW_DOWN = '<svg class="folderArrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>';

  function buildTreeFromPaths(paths) {
    var root = {};
    paths.forEach(function (path) {
      var parts = path.split("/").filter(Boolean);
      var curr = root;
      for (var i = 0; i < parts.length; i++) {
        var name = parts[i];
        var isFile = i === parts.length - 1;
        if (!curr[name]) {
          curr[name] = isFile ? { type: "file", path: path } : { type: "folder", children: {} };
        }
        if (!isFile) curr = curr[name].children;
      }
    });
    return objectToTree(root, "");
  }

  function objectToTree(obj, prefix) {
    var result = [];
    var keys = Object.keys(obj).sort();
    keys.forEach(function (k) {
      var item = obj[k];
      if (item.type === "file") {
        result.push({ name: k, type: "file", path: item.path });
      } else {
        var children = objectToTree(item.children, prefix + k + "/");
        result.push({ name: k, type: "folder", children: children });
      }
    });
    return result;
  }

  function renderFileTree(tree, container) {
    container.innerHTML = "";
    tree.forEach(function (node) { renderRec(container, node, 0); });
  }

  function renderRec(container, node, depth) {
    if (node.type === "file") {
      var el = document.createElement("div");
      el.className = "fileTreeItem fileTreeFile" + (node.path === currentFilePath ? " active" : "");
      el.dataset.path = node.path;
      el.style.paddingLeft = (depth * 12 + 8) + "px";
      el.innerHTML = ICON_FILE + "<span>" + escapeHtml(node.name) + "</span>";
      el.addEventListener("click", function () { loadFile(node.path); });
      container.appendChild(el);
    } else {
      var folderEl = document.createElement("div");
      folderEl.className = "fileTreeItem fileTreeFolder open";
      folderEl.style.paddingLeft = (depth * 12 + 8) + "px";
      folderEl.innerHTML = '<span class="folderArrowWrap">' + ICON_ARROW_DOWN + '</span>' + ICON_FOLDER + "<span>" + escapeHtml(node.name) + "</span>";
      folderEl.addEventListener("click", function (e) {
        e.stopPropagation();
        var isOpen = folderEl.classList.toggle("open");
        var arrowWrap = folderEl.querySelector(".folderArrowWrap");
        if (arrowWrap) arrowWrap.innerHTML = isOpen ? ICON_ARROW_DOWN : ICON_ARROW_RIGHT;
        var next = folderEl.nextElementSibling;
        if (next) next.classList.toggle("collapsed", !isOpen);
      });
      container.appendChild(folderEl);
      var childWrap = document.createElement("div");
      childWrap.className = "fileTreeChildren";
      (node.children || []).forEach(function (c) { renderRec(childWrap, c, depth + 1); });
      container.appendChild(childWrap);
    }
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function saveCurrentToCache() {
    if (!currentFilePath || !projectFiles.hasOwnProperty(currentFilePath)) return;
    var ed = window.getMonacoEditor && window.getMonacoEditor();
    if (ed) projectFiles[currentFilePath] = ed.getValue();
  }

  function loadFile(path) {
    if (!projectFiles.hasOwnProperty(path)) return;
    saveCurrentToCache();
    currentFilePath = path;
    var content = projectFiles[path];
    if (!originalFileContents[path]) originalFileContents[path] = content;
    var lang = window.getLangFromPath ? window.getLangFromPath(path) : "plaintext";
    if (window.updateEditor) window.updateEditor(content, lang);
    var list = document.getElementById("fileTreeList");
    if (list) {
      list.querySelectorAll(".fileTreeFile").forEach(function (el) {
        el.classList.toggle("active", el.dataset.path === path);
      });
    }
    try { localStorage.setItem("yui_workspace_current", path); } catch (e) {}
  }

  function readFilesRecursive(files, basePath, prefix) {
    var promises = [];
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      var path = f.webkitRelativePath || f.name;
      if (path.indexOf(basePath) === 0) path = path.slice(basePath.length).replace(/^\//, "");
      else if (prefix) path = prefix + path;
      if (f.isDirectory) continue;
      var p = new Promise(function (resolve) {
        var r = new FileReader();
        r.onload = function () {
          projectFiles[path] = r.result || "";
          resolve();
        };
        r.onerror = resolve;
        r.readAsText(f, "UTF-8");
      });
      promises.push(p);
    }
    return Promise.all(promises);
  }

  function importProject() {
    var input = document.getElementById("workspaceImportInput");
    if (!input) return;
    input.value = "";
    input.onchange = function () {
      var files = input.files;
      if (!files || files.length === 0) return;
      projectFiles = {};
      originalFileContents = {};
      var paths = [];
      var basePath = "";
      if (files[0].webkitRelativePath) {
        var parts = files[0].webkitRelativePath.split("/");
        basePath = parts[0] + "/";
        projectName = parts[0];
      }
      var fileArray = [];
      for (var i = 0; i < files.length; i++) {
        if (files[i].isDirectory) continue;
        var path = files[i].webkitRelativePath || files[i].name;
        if (basePath && path.indexOf(basePath) === 0) path = path.slice(basePath.length);
        paths.push(path);
        fileArray.push({ file: files[i], path: path });
      }
      var loaded = 0;
      fileArray.forEach(function (item) {
        var r = new FileReader();
        r.onload = function () {
          var content = r.result || "";
          projectFiles[item.path] = content;
          originalFileContents[item.path] = content;
          loaded++;
          if (loaded === fileArray.length) {
            projectTree = buildTreeFromPaths(paths);
            renderFileTree(projectTree, document.getElementById("fileTreeList"));
            document.getElementById("fileTreeEmpty").style.display = "none";
            document.getElementById("fileTreeList").style.display = "block";
            if (paths.length > 0) loadFile(paths[0]);
          }
        };
        r.readAsText(item.file, "UTF-8");
      });
    };
    input.click();
  }

  function exportZip() {
    if (Object.keys(projectFiles).length === 0) {
      alert("Importe um projeto primeiro.");
      return;
    }
    if (typeof JSZip === "undefined") {
      alert("JSZip não carregado. Tente recarregar a página.");
      return;
    }
    saveCurrentToCache();
    var zip = new JSZip();
    Object.keys(projectFiles).forEach(function (path) {
      zip.file(path, projectFiles[path]);
    });
    zip.generateAsync({ type: "blob" }).then(function (blob) {
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (projectName || "projeto") + ".zip";
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  function logToConsole(text, isError) {
    var el = document.getElementById("workspaceConsoleOutput");
    var actions = document.getElementById("workspaceConsoleActions");
    if (!el) return;
    el.textContent = text || "$ Aguardando execução...";
    el.classList.toggle("error", !!isError);
    el.classList.remove("success");
    if (!isError && text && text.indexOf("$ Salvos:") === 0) el.classList.add("success");
    if (isError) {
      lastConsoleError = text;
      if (actions) actions.style.display = "flex";
    } else {
      lastConsoleError = null;
      if (actions) actions.style.display = "none";
    }
  }

  function executeCode() {
    saveCurrentToCache();
    var ed = window.getMonacoEditor && window.getMonacoEditor();
    if (!ed) {
      logToConsole("$ Erro: Editor não disponível.", true);
      return;
    }
    var code = ed.getValue();
    var path = currentFilePath;
    var lang = path ? (window.getLangFromPath ? window.getLangFromPath(path) : "python") : "python";
    if (lang === "plaintext") lang = "python";
    if (!code.trim()) {
      logToConsole("$ Nenhum código para executar.", true);
      return;
    }
    var ts = new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
    logToConsole("[" + ts + "] $ Executando...", false);
    fetch("/api/sandbox/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code, lang: lang, timeout: 15 }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var executedAt = data.executed_at || "";
        var out = [];
        if (data.stdout) out.push(data.stdout.trim());
        if (data.stderr) out.push(data.stderr.trim());
        if (data.feedback) out.push("\n--- " + data.feedback + " ---");
        var text = out.join("\n") || "(nenhuma saída)";
        if (!data.ok) text = "ERRO (exit " + (data.exit_code || -1) + "):\n" + text;
        var prefix = executedAt ? "[" + executedAt + "] " : "";
        logToConsole(prefix + "$ " + text, !data.ok);
      })
      .catch(function (e) {
        logToConsole("$ Erro de rede: " + (e.message || String(e)), true);
      });
  }

  function syncToSandbox() {
    saveCurrentToCache();
    var files = [];
    Object.keys(projectFiles).forEach(function (path) {
      files.push({ path: path, content: projectFiles[path] });
    });
    if (files.length === 0) {
      var ed = window.getMonacoEditor && window.getMonacoEditor();
      if (ed && ed.getValue().trim()) {
        var path = currentFilePath || "main.py";
        files.push({ path: path, content: ed.getValue() });
      }
    }
    if (files.length === 0) {
      logToConsole("$ Nenhum arquivo para salvar no sandbox.", true);
      return;
    }
    logToConsole("$ Salvando " + files.length + " arquivo(s) no sandbox...", false);
    fetch("/api/sandbox/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files: files }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          logToConsole("$ Salvos: " + (data.saved || []).join(", "), false);
        } else {
          logToConsole("$ Erro: " + (data.error || "desconhecido"), true);
        }
      })
      .catch(function (e) {
        logToConsole("$ Erro de rede: " + (e.message || String(e)), true);
      });
  }

  function feedToYui() {
    saveCurrentToCache();
    var path = currentFilePath;
    var ed = window.getMonacoEditor && window.getMonacoEditor();
    var content = (path && projectFiles[path]) ? projectFiles[path] : (ed ? ed.getValue() : "");
    if (!content) {
      alert("Nenhum arquivo selecionado ou editor vazio.");
      return;
    }
    var lang = path ? (window.getLangFromPath ? window.getLangFromPath(path) : "text") : "text";
    var filename = path ? path.split("/").pop() : "codigo";
    var msg = document.getElementById("msg");
    if (!msg) return;
    var prefix = "Analise este arquivo e sugira melhorias de arquitetura e refatoração:\n\n```" + lang + "\n";
    msg.value = prefix + content + "\n```";
    msg.focus();
  }

  function updateWorkspacePreview() {
    saveCurrentToCache();
    var frame = document.getElementById("workspacePreviewFrame");
    var empty = document.getElementById("workspacePreviewEmpty");
    var wrap = frame && frame.closest(".workspacePreviewWrap");
    if (!frame || !empty) return;
    var html = "";
    var path = currentFilePath;
    if (path && /\.(html|htm)$/i.test(path)) {
      html = projectFiles[path] || "";
    }
    if (!html) {
      var idx = Object.keys(projectFiles).find(function (p) { return /index\.html?$/i.test(p); });
      if (idx) html = projectFiles[idx] || "";
    }
    if (!html || !html.trim()) {
      frame.srcdoc = "";
      frame.style.display = "none";
      empty.style.display = "flex";
      if (wrap) wrap.classList.remove("has-content");
      return;
    }
    html = html.replace(/<link\s+[^>]*href=["']([^"']+\.css)["'][^>]*>/gi, function (m, href) {
      var cssPath = href.replace(/^\//, "");
      var css = projectFiles[cssPath] || projectFiles["style.css"] || "";
      var keys = Object.keys(projectFiles);
      for (var i = 0; i < keys.length; i++) {
        if (keys[i].toLowerCase().endsWith(".css") && keys[i].indexOf(cssPath) >= 0) {
          css = projectFiles[keys[i]] || "";
          break;
        }
      }
      return css ? "<style>" + css + "</style>" : m;
    });
    try {
      frame.srcdoc = html;
      frame.style.display = "block";
      empty.style.display = "none";
      if (wrap) wrap.classList.add("has-content");
    } catch (e) {
      empty.style.display = "flex";
      empty.textContent = "Erro ao renderizar preview.";
    }
  }

  function showDiffView() {
    saveCurrentToCache();
    var path = currentFilePath;
    if (!path) {
      alert("Selecione um arquivo na árvore para ver o diff.");
      return;
    }
    var original = originalFileContents[path] || "";
    var current = projectFiles[path] || "";
    if (original === current) {
      alert("Nenhuma alteração neste arquivo.");
      return;
    }
    var overlay = document.getElementById("workspaceDiffOverlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "workspaceDiffOverlay";
      overlay.className = "workspaceDiffOverlay";
      overlay.innerHTML = '<div class="workspaceDiffModal"><div class="workspaceDiffHeader"><span>Diff: ' + escapeHtml(path) + '</span><button type="button" class="workspaceDiffClose">×</button></div><div class="workspaceDiffBody"><div class="workspaceDiffCol"><h4>Original</h4><pre class="workspaceDiffPre" id="workspaceDiffOriginal"></pre></div><div class="workspaceDiffCol"><h4>Atual</h4><pre class="workspaceDiffPre" id="workspaceDiffCurrent"></pre></div></div></div>';
      overlay.querySelector(".workspaceDiffClose").onclick = function () { overlay.style.display = "none"; };
      overlay.onclick = function (e) { if (e.target === overlay) overlay.style.display = "none"; };
      document.body.appendChild(overlay);
    }
    overlay.querySelector("#workspaceDiffOriginal").textContent = original;
    overlay.querySelector("#workspaceDiffCurrent").textContent = current;
    overlay.querySelector(".workspaceDiffHeader span").textContent = "Diff: " + path;
    overlay.style.display = "flex";
  }

  function initWorkspaceProject() {
    var tabs = document.getElementById("workspaceTabs");
    if (tabs) {
      tabs.querySelectorAll(".workspaceTab").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var tab = btn.getAttribute("data-tab");
          tabs.querySelectorAll(".workspaceTab").forEach(function (b) { b.classList.remove("active"); });
          btn.classList.add("active");
          document.querySelectorAll(".workspaceTabContent").forEach(function (c) { c.style.display = "none"; });
          var content = document.getElementById("workspaceTab" + (tab === "editor" ? "Editor" : tab === "preview" ? "Preview" : "Editor"));
          if (content) {
            content.style.display = "flex";
            if (tab === "preview") updateWorkspacePreview();
          }
        });
      });
    }
    document.addEventListener("workspacePreviewUpdate", updateWorkspacePreview);
    var importBtn = document.getElementById("workspaceImport");
    var exportBtn = document.getElementById("workspaceExport");
    var feedBtn = document.getElementById("workspaceFeedYui");
    var runBtn = document.getElementById("workspaceRun");
    var syncBtn = document.getElementById("workspaceSyncSandbox");
    var diffBtn = document.getElementById("workspaceDiff");
    var suggestBtn = document.getElementById("workspaceSuggestFix");
    if (importBtn) importBtn.addEventListener("click", importProject);
    if (exportBtn) exportBtn.addEventListener("click", exportZip);
    if (feedBtn) feedBtn.addEventListener("click", feedToYui);
    if (runBtn) runBtn.addEventListener("click", executeCode);
    if (syncBtn) syncBtn.addEventListener("click", syncToSandbox);
    if (diffBtn) diffBtn.addEventListener("click", showDiffView);
    if (suggestBtn) {
      suggestBtn.addEventListener("click", function () {
        var msg = document.getElementById("msg");
        if (!msg) return;
        var code = "";
        var ed = window.getMonacoEditor && window.getMonacoEditor();
        if (ed) code = ed.getValue();
        var err = lastConsoleError || "erro desconhecido";
        var prompt = "O código que você gerou deu erro. Por favor corrija.\n\nErro:\n" + err + (code ? "\n\nCódigo atual:\n```\n" + code.slice(0, 1000) + "\n```" : "");
        msg.value = prompt;
        msg.focus();
        try {
          sessionStorage.setItem("yui_lesson_error", err);
          sessionStorage.setItem("yui_lesson_context", code ? code.slice(0, 1500) : "");
        } catch (e) {}
        var switcher = document.getElementById("modelSwitcher");
        if (switcher) {
          switcher.value = "heathcliff";
          switcher.dispatchEvent(new Event("change"));
        }
      });
    }
    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.key === "Enter") {
        var mainSplit = document.querySelector(".mainSplit");
        if (mainSplit && (mainSplit.classList.contains("editor-hidden") || mainSplit.classList.contains("workspaceCollapsed"))) return;
        e.preventDefault();
        executeCode();
      }
    });
  }

  function removeFileFromWorkspace(path) {
    delete projectFiles[path];
    delete originalFileContents[path];
    var paths = Object.keys(projectFiles);
    projectTree = buildTreeFromPaths(paths);
    var list = document.getElementById("fileTreeList");
    var empty = document.getElementById("fileTreeEmpty");
    if (list) {
      if (paths.length === 0) {
        list.style.display = "none";
        if (empty) empty.style.display = "block";
      } else {
        renderFileTree(projectTree, list);
      }
    }
    if (currentFilePath === path) {
      currentFilePath = paths[0] || null;
      if (currentFilePath) loadFile(currentFilePath);
      else if (window.updateEditor) window.updateEditor("", "plaintext");
    }
  }

  function addFileToWorkspace(path, content) {
    projectFiles[path] = content || "";
    if (!originalFileContents[path]) originalFileContents[path] = content || "";
    var paths = Object.keys(projectFiles);
    projectTree = buildTreeFromPaths(paths);
    var list = document.getElementById("fileTreeList");
    var empty = document.getElementById("fileTreeEmpty");
    if (list) {
      list.style.display = "block";
      renderFileTree(projectTree, list);
    }
    if (empty) empty.style.display = "none";
    loadFile(path);
    document.dispatchEvent(new CustomEvent("workspaceFileAdded", { detail: { path: path } }));
  }

  window.initWorkspaceProject = initWorkspaceProject;
  window.loadWorkspaceFile = loadFile;
  window.updateWorkspacePreview = updateWorkspacePreview;
  window.addFileToWorkspace = addFileToWorkspace;
  window.removeFileFromWorkspace = removeFileFromWorkspace;
  window.getWorkspaceContext = function () {
    var files = Object.keys(projectFiles || {});
    var active = currentFilePath ? [currentFilePath] : [];
    files.forEach(function (p) {
      if (active.indexOf(p) < 0) active.push(p);
    });
    return {
      active_files: active,
      console_errors: lastConsoleError ? [lastConsoleError] : []
    };
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWorkspaceProject);
  } else {
    initWorkspaceProject();
  }
})();
