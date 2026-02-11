/**
 * YUI Workspace — Monaco Editor integrado
 * Carregamento assíncrono para não atrasar o app no Zeabur.
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var monacoLoaded = false;
  var monacoLoadPromise = null;
  var currentLang = "text";

  function loadMonacoAsync() {
    if (monacoLoaded) return Promise.resolve();
    if (monacoLoadPromise) return monacoLoadPromise;

    monacoLoadPromise = new Promise(function (resolve, reject) {
      if (window.monaco && window.monaco.editor) {
        monacoLoaded = true;
        resolve();
        return;
      }
      var baseUrl = "https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min";
      var script = document.createElement("script");
      script.src = baseUrl + "/vs/loader.js";
      script.async = true;
      script.onload = function () {
        window.require.config({
          paths: { vs: baseUrl + "/vs" },
          "vs/nls": { availableLanguages: {} },
        });
        window.require(["vs/editor/editor.main"], function () {
          monacoLoaded = true;
          resolve();
        }, reject);
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return monacoLoadPromise;
  }

  function initMonacoEditor() {
    var container = document.getElementById("monacoContainer");
    if (!container || monacoEditor) return;

    loadMonacoAsync().then(function () {
      monacoEditor = window.monaco.editor.create(container, {
        value: "// Cole código aqui ou use «Enviar para o Workspace» nos blocos do chat.\n",
        language: "plaintext",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "'Fira Code', 'JetBrains Mono', Consolas, monospace",
        scrollBeyondLastLine: false,
        padding: { top: 12 },
      });
    }).catch(function (e) {
      console.warn("Monaco editor não carregou:", e);
      container.innerHTML = "<div class=\"workspaceFallback\">Editor não disponível. Use o botão Copiar nos blocos de código.</div>";
    });
  }

  function getLangToMonaco(lang) {
    var map = {
      js: "javascript", javascript: "javascript",
      ts: "typescript", typescript: "typescript",
      tsx: "typescript", jsx: "javascript",
      py: "python", python: "python",
      json: "json", html: "html", css: "css",
      md: "markdown", markdown: "markdown",
      java: "java", c: "c", cpp: "cpp",
      sh: "shell", bash: "shell", bash: "shell",
      yaml: "yaml", yml: "yaml",
    };
    return map[(lang || "").toLowerCase()] || "plaintext";
  }

  function getLangToExt(lang) {
    var map = {
      js: "js", javascript: "js", ts: "ts", typescript: "ts",
      tsx: "tsx", jsx: "jsx", py: "py", python: "py",
      json: "json", html: "html", css: "css", md: "md",
      java: "java", yaml: "yml", yml: "yml",
    };
    return map[(lang || "").toLowerCase()] || "txt";
  }

  window.updateEditor = function (code, lang) {
    currentLang = lang || "text";
    if (!monacoEditor) {
      initMonacoEditor();
      var checkEditor = setInterval(function () {
        if (monacoEditor) {
          clearInterval(checkEditor);
          monacoEditor.setValue(code || "");
          try {
            var model = monacoEditor.getModel();
            if (model) window.monaco.editor.setModelLanguage(model, getLangToMonaco(currentLang));
          } catch (e) {}
          triggerEditorPulse();
        }
      }, 100);
      setTimeout(function () { clearInterval(checkEditor); }, 3000);
      return;
    }
    monacoEditor.setValue(code || "");
    try {
      var model = monacoEditor.getModel();
      if (model) window.monaco.editor.setModelLanguage(model, getLangToMonaco(currentLang));
    } catch (e) {}
    triggerEditorPulse();
  };

  function triggerEditorPulse() {
    var panel = document.getElementById("workspacePanel");
    if (panel) {
      panel.classList.remove("editorPulse");
      panel.offsetHeight;
      panel.classList.add("editorPulse");
      setTimeout(function () { panel.classList.remove("editorPulse"); }, 1200);
    }
  }

  function workspaceCopy() {
    if (!monacoEditor) return;
    var content = monacoEditor.getValue();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(content).then(function () {
        var btn = document.getElementById("workspaceCopy");
        if (btn) {
          var orig = btn.textContent;
          btn.textContent = "Copiado!";
          setTimeout(function () { btn.textContent = orig; }, 1500);
        }
      }).catch(function () {});
    }
  }

  function workspaceDownload() {
    if (!monacoEditor) return;
    var content = monacoEditor.getValue();
    var ext = getLangToExt(currentLang);
    var filename = "code." + ext;
    var blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function initWorkspaceButtons() {
    var copyBtn = document.getElementById("workspaceCopy");
    var downloadBtn = document.getElementById("workspaceDownload");
    if (copyBtn) copyBtn.addEventListener("click", workspaceCopy);
    if (downloadBtn) downloadBtn.addEventListener("click", workspaceDownload);
  }

  window.initYuiWorkspace = function () {
    initWorkspaceButtons();
    initMonacoEditor();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWorkspaceButtons);
  } else {
    initWorkspaceButtons();
  }
})();
