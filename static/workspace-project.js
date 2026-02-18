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
  var selectedTreePath = null;
  var selectedTreeIsDir = false;
  var projectName = "projeto";
  var lastConsoleError = null;
  var sandboxMode = false;
  var sandboxExpandedChildren = {};
  var workspaceProjectInitialized = false;

  if (!window.getLangFromPath) {
    window.getLangFromPath = function (path) {
      if (!path) return "plaintext";
      var ext = (path.split(".").pop() || "").toLowerCase();
      var map = { py: "python", js: "javascript", ts: "typescript", jsx: "javascript", tsx: "javascript", html: "html", css: "css", json: "json", md: "markdown" };
      return map[ext] || "plaintext";
    };
  }

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

  function updateTreeSelection(path, isDir, el) {
    selectedTreePath = path || null;
    selectedTreeIsDir = !!isDir;
    var list = document.getElementById("fileTreeList");
    if (!list) return;
    list.querySelectorAll(".fileTreeItem").forEach(function (n) { n.classList.remove("selected"); });
    if (el) el.classList.add("selected");
  }

  function renderRec(container, node, depth) {
    if (node.type === "file") {
      var el = document.createElement("div");
      el.className = "fileTreeItem fileTreeFile" + (node.path === currentFilePath ? " active" : "");
      el.dataset.path = node.path;
      el.style.paddingLeft = (depth * 12 + 8) + "px";
      el.innerHTML = ICON_FILE + "<span>" + escapeHtml(node.name) + "</span>";
      el.addEventListener("click", function () {
        updateTreeSelection(node.path, false, el);
        loadFile(node.path);
      });
      container.appendChild(el);
    } else {
      var folderEl = document.createElement("div");
      folderEl.className = "fileTreeItem fileTreeFolder";
      folderEl.style.paddingLeft = (depth * 12 + 8) + "px";
      folderEl.innerHTML = '<span class="folderArrowWrap">' + ICON_ARROW_RIGHT + '</span>' + ICON_FOLDER + "<span>" + escapeHtml(node.name) + "</span>";
      folderEl.addEventListener("click", function (e) {
        e.stopPropagation();
        updateTreeSelection(node.name, true, folderEl);
        var isOpen = folderEl.classList.toggle("open");
        var arrowWrap = folderEl.querySelector(".folderArrowWrap");
        if (arrowWrap) arrowWrap.innerHTML = isOpen ? ICON_ARROW_DOWN : ICON_ARROW_RIGHT;
        var next = folderEl.nextElementSibling;
        if (next) next.classList.toggle("collapsed", !isOpen);
      });
      container.appendChild(folderEl);
      var childWrap = document.createElement("div");
      childWrap.className = "fileTreeChildren collapsed";
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
    saveCurrentToCache();
    if (!projectFiles.hasOwnProperty(path)) {
      if (sandboxMode) {
        fetch((window.apiUrl || function(p){return p;})("/api/sandbox/read?path=" + encodeURIComponent(path)))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.ok) {
              projectFiles[path] = data.content || "";
              if (!originalFileContents[path]) originalFileContents[path] = projectFiles[path];
              doLoadFile(path);
            } else {
              logToConsole("$ Erro ao abrir arquivo do sandbox: " + (data.error || "desconhecido"), true);
            }
          })
          .catch(function (e) {
            logToConsole("$ Erro de rede ao abrir arquivo: " + (e.message || String(e)), true);
          });
        return;
      }
      return;
    }
    doLoadFile(path);
  }

  function doLoadFile(path) {
    currentFilePath = path;
    var content = projectFiles[path] || "";
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

  function loadFromSandbox() {
    sandboxMode = true;
    sandboxExpandedChildren = {};
    projectFiles = {};
    originalFileContents = {};
    projectTree = [];
    currentFilePath = null;
    var list = document.getElementById("fileTreeList");
    var empty = document.getElementById("fileTreeEmpty");
    if (list) list.innerHTML = "<div class='fileTreeLoading'>Carregando...</div>";
    if (empty) empty.style.display = "none";
    if (list) list.style.display = "block";
    fetch((window.apiUrl || function(p){return p;})("/api/sandbox/list?path=."))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) {
          if (list) list.innerHTML = "<div class='fileTreeLoading'>" + (data.error || "Erro") + "</div>";
          return;
        }
        var entries = data.entries || [];
        if (entries.length === 0) {
          if (list) list.style.display = "none";
          if (empty) {
            empty.textContent = "Sandbox vazio. Importe um projeto ou crie arquivos pelo chat.";
            empty.style.display = "block";
          }
          return;
        }
        renderSandboxTree(entries, list, 0, "");
      })
      .catch(function () {
        if (list) list.innerHTML = "<div class='fileTreeLoading'>Erro ao carregar sandbox</div>";
      });
  }

  function renderSandboxTree(entries, container, depth, parentPath) {
    container.innerHTML = "";
    entries.forEach(function (e) {
      var path = e.path || (parentPath ? parentPath + "/" + e.name : e.name);
      if (e.is_dir) {
        var folderEl = document.createElement("div");
        folderEl.className = "fileTreeItem fileTreeFolder";
        folderEl.style.paddingLeft = (depth * 12 + 8) + "px";
        folderEl.dataset.path = path;
        folderEl.innerHTML = '<span class="folderArrowWrap">' + ICON_ARROW_RIGHT + '</span>' + ICON_FOLDER + "<span>" + escapeHtml(e.name) + "</span>";
        var childWrap = document.createElement("div");
        childWrap.className = "fileTreeChildren collapsed";
        childWrap.dataset.path = path;
        folderEl.addEventListener("click", function (ev) {
          ev.stopPropagation();
          updateTreeSelection(path, true, folderEl);
          var isOpen = folderEl.classList.toggle("open");
          var arrowWrap = folderEl.querySelector(".folderArrowWrap");
          if (arrowWrap) arrowWrap.innerHTML = isOpen ? ICON_ARROW_DOWN : ICON_ARROW_RIGHT;
          childWrap.classList.toggle("collapsed", !isOpen);
          if (isOpen && !sandboxExpandedChildren[path]) {
            sandboxExpandedChildren[path] = true;
            childWrap.innerHTML = "<div class='fileTreeLoading'>Carregando...</div>";
            fetch((window.apiUrl || function(p){return p;})("/api/sandbox/list?path=" + encodeURIComponent(path)))
              .then(function (r) { return r.json(); })
              .then(function (data) {
                if (data.ok) renderSandboxTree(data.entries || [], childWrap, depth + 1, path);
                else childWrap.innerHTML = "";
              })
              .catch(function () { childWrap.innerHTML = ""; });
          }
        });
        container.appendChild(folderEl);
        container.appendChild(childWrap);
      } else {
        var fileEl = document.createElement("div");
        fileEl.className = "fileTreeItem fileTreeFile" + (path === currentFilePath ? " active" : "");
        fileEl.dataset.path = path;
        fileEl.style.paddingLeft = (depth * 12 + 8) + "px";
        fileEl.innerHTML = ICON_FILE + "<span>" + escapeHtml(e.name) + "</span>";
        fileEl.addEventListener("click", function () {
          updateTreeSelection(path, false, fileEl);
          loadFile(path);
        });
        container.appendChild(fileEl);
      }
    });
  }

  function _parentDir(path) {
    if (!path || path.indexOf("/") < 0) return "";
    return path.replace(/\/[^/]+$/, "");
  }

  function _joinPath(dir, name) {
    var d = (dir || "").replace(/^\/+|\/+$/g, "");
    var n = (name || "").replace(/^\/+|\/+$/g, "");
    return d ? (d + "/" + n) : n;
  }

  function _refreshLocalTreeAndOpen(pathToOpen) {
    var paths = Object.keys(projectFiles);
    projectTree = buildTreeFromPaths(paths);
    var list = document.getElementById("fileTreeList");
    var empty = document.getElementById("fileTreeEmpty");
    if (list) {
      if (paths.length === 0) {
        list.style.display = "none";
      } else {
        list.style.display = "block";
        renderFileTree(projectTree, list);
      }
    }
    if (empty) empty.style.display = paths.length === 0 ? "block" : "none";
    if (pathToOpen && projectFiles.hasOwnProperty(pathToOpen)) {
      loadFile(pathToOpen);
    }
  }

  function createWorkspaceFile() {
    var baseDir = selectedTreePath ? (selectedTreeIsDir ? selectedTreePath : _parentDir(selectedTreePath)) : _parentDir(currentFilePath || "");
    var name = (window.prompt("Nome do novo arquivo (ex: src/main.py):", "main.py") || "").trim();
    if (!name) return;
    if (name.indexOf("..") >= 0) return alert("Caminho inválido.");
    var path = _joinPath(baseDir, name);

    if (sandboxMode) {
      fetch((window.apiUrl || function(p){return p;})("/api/sandbox/files"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create_file", path: path, content: "" }),
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (!data.ok) return logToConsole("$ Erro ao criar arquivo: " + (data.error || "desconhecido"), true);
        projectFiles[path] = "";
        originalFileContents[path] = "";
        _refreshLocalTreeAndOpen(path);
        updateTreeSelection(path, false);
      }).catch(function (e) {
        logToConsole("$ Erro de rede ao criar arquivo: " + (e.message || String(e)), true);
      });
      return;
    }

    projectFiles[path] = "";
    originalFileContents[path] = "";
    _refreshLocalTreeAndOpen(path);
    updateTreeSelection(path, false);
  }

  function createWorkspaceFolder() {
    var baseDir = selectedTreePath ? (selectedTreeIsDir ? selectedTreePath : _parentDir(selectedTreePath)) : _parentDir(currentFilePath || "");
    var name = (window.prompt("Nome da nova pasta:", "nova-pasta") || "").trim();
    if (!name) return;
    if (name.indexOf("..") >= 0) return alert("Caminho inválido.");
    var path = _joinPath(baseDir, name);

    if (!sandboxMode) {
      projectFiles[path + "/.gitkeep"] = "";
      originalFileContents[path + "/.gitkeep"] = "";
      var paths = Object.keys(projectFiles);
      projectTree = buildTreeFromPaths(paths);
      var list = document.getElementById("fileTreeList");
      var empty = document.getElementById("fileTreeEmpty");
      if (list) { list.style.display = "block"; renderFileTree(projectTree, list); }
      if (empty) empty.style.display = "none";
      return;
    }

    fetch((window.apiUrl || function(p){return p;})("/api/sandbox/files"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "create_folder", path: path }),
    }).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.ok) return logToConsole("$ Erro ao criar pasta: " + (data.error || "desconhecido"), true);
      loadFromSandbox();
    }).catch(function (e) {
      logToConsole("$ Erro de rede ao criar pasta: " + (e.message || String(e)), true);
    });
  }

  function renameWorkspaceEntry() {
    if (!selectedTreePath) {
      alert("Selecione um arquivo/pasta na árvore para renomear.");
      return;
    }
    var oldPath = selectedTreePath;
    var baseDir = _parentDir(oldPath);
    var currentName = oldPath.split("/").pop();
    var newName = (window.prompt("Novo nome:", currentName) || "").trim();
    if (!newName || newName === currentName) return;
    if (newName.indexOf("..") >= 0 || newName.indexOf("/") >= 0) return alert("Nome inválido.");
    var newPath = _joinPath(baseDir, newName);

    // rename = create + delete (compatível com API atual)
    if (selectedTreeIsDir) {
      alert("Renomear pasta ainda não está habilitado. Renomeie os arquivos dentro da pasta.");
      return;
    }

    var content = projectFiles[oldPath] || "";
    if (sandboxMode) {
      fetch((window.apiUrl || function(p){return p;})("/api/sandbox/files"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create_file", path: newPath, content: content }),
      }).then(function (r) { return r.json(); }).then(function (created) {
        if (!created.ok) return logToConsole("$ Erro ao renomear arquivo: " + (created.error || "desconhecido"), true);
        return fetch((window.apiUrl || function(p){return p;})("/api/sandbox/files"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "delete", path: oldPath }),
        }).then(function (r) { return r.json(); }).then(function (deleted) {
          if (!deleted.ok) return logToConsole("$ Erro ao remover arquivo antigo: " + (deleted.error || "desconhecido"), true);
          delete projectFiles[oldPath];
          delete originalFileContents[oldPath];
          projectFiles[newPath] = content;
          originalFileContents[newPath] = content;
          _refreshLocalTreeAndOpen(newPath);
          updateTreeSelection(newPath, false);
        });
      }).catch(function (e) {
        logToConsole("$ Erro de rede ao renomear arquivo: " + (e.message || String(e)), true);
      });
      return;
    }

    delete projectFiles[oldPath];
    delete originalFileContents[oldPath];
    projectFiles[newPath] = content;
    originalFileContents[newPath] = content;
    _refreshLocalTreeAndOpen(newPath);
    updateTreeSelection(newPath, false);
  }

  function deleteWorkspaceEntry() {
    if (!selectedTreePath) {
      alert("Selecione um arquivo/pasta na árvore para excluir.");
      return;
    }
    if (!window.confirm("Tem certeza que deseja excluir: " + selectedTreePath + " ?")) return;
    var path = selectedTreePath;

    if (sandboxMode) {
      fetch((window.apiUrl || function(p){return p;})("/api/sandbox/files"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", path: path }),
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (!data.ok) return logToConsole("$ Erro ao excluir: " + (data.error || "desconhecido"), true);
        Object.keys(projectFiles).forEach(function (k) {
          if (k === path || k.indexOf(path + "/") === 0) {
            delete projectFiles[k];
            delete originalFileContents[k];
          }
        });
        if (currentFilePath && (currentFilePath === path || currentFilePath.indexOf(path + "/") === 0)) {
          currentFilePath = null;
          if (window.updateEditor) window.updateEditor("", "plaintext");
        }
        _refreshLocalTreeAndOpen(Object.keys(projectFiles)[0] || null);
        updateTreeSelection(null, false);
      }).catch(function (e) {
        logToConsole("$ Erro de rede ao excluir: " + (e.message || String(e)), true);
      });
      return;
    }

    Object.keys(projectFiles).forEach(function (k) {
      if (k === path || k.indexOf(path + "/") === 0) {
        delete projectFiles[k];
        delete originalFileContents[k];
      }
    });
    if (currentFilePath && (currentFilePath === path || currentFilePath.indexOf(path + "/") === 0)) {
      currentFilePath = null;
      if (window.updateEditor) window.updateEditor("", "plaintext");
    }
    _refreshLocalTreeAndOpen(Object.keys(projectFiles)[0] || null);
    updateTreeSelection(null, false);
  }

  function importProject() {
    var input = document.getElementById("workspaceImportInput");
    if (!input) return;
    input.value = "";
    input.onchange = function () {
      var files = input.files;
      if (!files || files.length === 0) return;
      sandboxMode = false;
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
      if (fileArray.length === 0) {
        logToConsole("$ Nenhum arquivo válido encontrado para importar.", true);
        return;
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
    if (sandboxMode) {
      logToConsole("$ Compactando projeto completo do sandbox...", false);
      fetch((window.apiUrl || function(p){return p;})("/api/sandbox/zip"))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data || !data.ok || !data.url) {
            throw new Error((data && data.error) || "Não foi possível compactar o sandbox.");
          }
          var a = document.createElement("a");
          a.href = data.url;
          a.download = data.filename || "workspace.zip";
          a.click();
          logToConsole("$ ZIP do projeto pronto para download.", false);
        })
        .catch(function (e) {
          logToConsole("$ Erro ao compactar projeto: " + (e.message || String(e)), true);
          alert("Não foi possível compactar o projeto completo agora.");
        });
      return;
    }

    if (Object.keys(projectFiles).length === 0) {
      alert("Importe um projeto primeiro.");
      return;
    }
    if (typeof JSZip === "undefined") {
      if (window.loadWorkspaceLibs) {
        window.loadWorkspaceLibs(function () {
          if (typeof JSZip === "undefined") {
            alert("JSZip não carregado. Tente recarregar a página.");
            return;
          }
          exportZip();
        });
        return;
      }
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
      logToConsole("$ ZIP do projeto pronto para download.", false);
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
    var filesToSync = [];
    Object.keys(projectFiles).forEach(function (path) {
      filesToSync.push({ path: path, content: projectFiles[path] });
    });
    if (filesToSync.length === 0 && code.trim()) {
      filesToSync.push({ path: currentFilePath || "main.py", content: code });
    }
    var path = currentFilePath;
    var lang = path ? (window.getLangFromPath ? window.getLangFromPath(path) : "python") : "python";
    if (lang === "plaintext") lang = "python";
    // Sandbox executor suporta python/py e javascript/js/node.
    var langMap = {
      python: "python",
      javascript: "javascript",
      js: "javascript",
      node: "javascript",
      typescript: "javascript",
      ts: "javascript",
      jsx: "javascript",
      tsx: "javascript",
    };
    lang = langMap[lang] || lang;
    if (lang !== "python" && lang !== "javascript") {
      logToConsole("$ Linguagem não suportada para executar aqui: " + String(lang) + ". Use Python/JS ou terminal.", true);
      return;
    }
    if (!code.trim()) {
      logToConsole("$ Nenhum código para executar.", true);
      return;
    }
    var ts = new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "medium" });
    logToConsole("[" + ts + "] $ Executando...", false);
    function run() {
    fetch((window.apiUrl || function(p){return p;})("/api/sandbox/execute"), {
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
    if (filesToSync.length > 0) {
      fetch((window.apiUrl || function(p){return p;})("/api/sandbox/save"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: filesToSync }),
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (data.ok) run();
        else logToConsole("$ Erro ao salvar: " + (data.error || "desconhecido"), true);
      }).catch(function (e) {
        logToConsole("$ Erro ao salvar: " + (e.message || String(e)), true);
      });
    } else {
      run();
    }
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
    fetch((window.apiUrl || function(p){return p;})("/api/sandbox/save"), {
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
    if (document.hidden) return;
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
    var linkedCssHrefs = [];
    html.replace(/<link\s+[^>]*href=["']([^"']+\.css)["'][^>]*>/gi, function (_, href) {
      var h = href.replace(/^\//, "").replace(/^\.\//, "").toLowerCase();
      linkedCssHrefs.push(h);
      linkedCssHrefs.push(h.split("/").pop());
    });
    var htmlFolder = path ? path.replace(/\/[^/]+$/, "").replace(/\/$/, "") : "";
    var htmlFolderPrefix = htmlFolder ? htmlFolder + "/" : "";
    var injectedCss = [];
    Object.keys(projectFiles).forEach(function (p) {
      if (!/\.css$/i.test(p)) return;
      var fileFolder = p.replace(/\/[^/]+$/, "").replace(/\/$/, "");
      var fileFolderPrefix = fileFolder ? fileFolder + "/" : "";
      var inSameFolder = fileFolderPrefix === htmlFolderPrefix || (htmlFolder === "" && fileFolder === "");
      if (!inSameFolder) return;
      var baseName = p.split("/").pop().toLowerCase();
      if (linkedCssHrefs.indexOf(baseName) >= 0 || linkedCssHrefs.indexOf(p.toLowerCase()) >= 0) return;
      injectedCss.push(projectFiles[p] || "");
    });
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
    var styleCss = projectFiles["style.css"] || projectFiles["Style.css"];
    if (styleCss && injectedCss.indexOf(styleCss) < 0 && !/<link[^>]*href=["'][^"']*style\.css["']/i.test(html)) {
      injectedCss.push(styleCss);
    }
    if (injectedCss.length > 0) {
      var cssBlock = "<style>" + injectedCss.join("\n") + "</style>";
      if (/<head[^>]*>/i.test(html)) {
        html = html.replace(/<head([^>]*)>/i, "<head$1>" + cssBlock);
      } else if (/<html[^>]*>/i.test(html)) {
        html = html.replace(/<html([^>]*)>/i, "<html$1><head>" + cssBlock + "</head>");
      } else {
        html = cssBlock + html;
      }
    }
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
    if (workspaceProjectInitialized) return;
    workspaceProjectInitialized = true;
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
    var previewDebounce = null;
    document.addEventListener("workspacePreviewUpdate", function () {
      if (document.hidden) return;
      if (previewDebounce) clearTimeout(previewDebounce);
      previewDebounce = setTimeout(function () {
        previewDebounce = null;
        updateWorkspacePreview();
      }, 400);
    });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        var f = document.getElementById("workspacePreviewFrame");
        if (f) { f.srcdoc = ""; f.style.display = "none"; }
      }
    });
    var importBtn = document.getElementById("workspaceImport");
    var exportBtn = document.getElementById("workspaceExport");
    var feedBtn = document.getElementById("workspaceFeedYui");
    var runBtn = document.getElementById("workspaceRun");
    var newFileBtn = document.getElementById("workspaceNewFile");
    var newFolderBtn = document.getElementById("workspaceNewFolder");
    var renameBtn = document.getElementById("workspaceRename");
    var deleteBtn = document.getElementById("workspaceDelete");
    var syncBtn = document.getElementById("workspaceSyncSandbox");
    var diffBtn = document.getElementById("workspaceDiff");
    var suggestBtn = document.getElementById("workspaceSuggestFix");
    var loadSbBtn = document.getElementById("workspaceLoadSandbox");
    if (loadSbBtn) loadSbBtn.addEventListener("click", loadFromSandbox);
    if (importBtn) importBtn.addEventListener("click", importProject);
    if (exportBtn) exportBtn.addEventListener("click", exportZip);
    if (feedBtn) feedBtn.addEventListener("click", feedToYui);
    if (runBtn) runBtn.addEventListener("click", executeCode);
    if (newFileBtn) newFileBtn.addEventListener("click", createWorkspaceFile);
    if (newFolderBtn) newFolderBtn.addEventListener("click", createWorkspaceFolder);
    if (renameBtn) renameBtn.addEventListener("click", renameWorkspaceEntry);
    if (deleteBtn) deleteBtn.addEventListener("click", deleteWorkspaceEntry);
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

    if (Object.keys(projectFiles).length === 0) {
      loadFromSandbox();
    }
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

  window.initWorkspaceProjectLazy = initWorkspaceProject;
})();
