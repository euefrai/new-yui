/**
 * YUI Workspace — Editor de projetos com File Tree
 * Importar pasta, trocar arquivos, exportar ZIP, Alimentar Yui
 */
(function () {
  "use strict";

  var projectFiles = {};
  var projectTree = [];
  var currentFilePath = null;
  var projectName = "projeto";

  var ICON_FOLDER = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
  var ICON_FILE = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';

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
      folderEl.innerHTML = ICON_FOLDER + "<span>" + escapeHtml(node.name) + "</span>";
      folderEl.addEventListener("click", function (e) {
        e.stopPropagation();
        folderEl.classList.toggle("open");
        var next = folderEl.nextElementSibling;
        if (next) next.classList.toggle("collapsed", !folderEl.classList.contains("open"));
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
          projectFiles[item.path] = r.result || "";
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

  function initWorkspaceProject() {
    var importBtn = document.getElementById("workspaceImport");
    var exportBtn = document.getElementById("workspaceExport");
    var feedBtn = document.getElementById("workspaceFeedYui");
    if (importBtn) importBtn.addEventListener("click", importProject);
    if (exportBtn) exportBtn.addEventListener("click", exportZip);
    if (feedBtn) feedBtn.addEventListener("click", feedToYui);
  }

  window.initWorkspaceProject = initWorkspaceProject;
  window.loadWorkspaceFile = loadFile;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWorkspaceProject);
  } else {
    initWorkspaceProject();
  }
})();
