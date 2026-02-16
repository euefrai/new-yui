/**
 * YUI Workspace — Monaco Editor & Smart Preview
 * Estilo Cursor IDE com injeção automática de CSS e efeitos visuais.
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var monacoLoaded = false;
  var monacoLoadPromise = null;
  var currentLang = "text";
  var workspaceButtonsBound = false;

  // 1. Carregamento Assíncrono do Monaco (Evita travamentos e erros de Mixed Content)
  function loadMonacoAsync() {
    if (monacoLoaded) return Promise.resolve();
    if (monacoLoadPromise) return monacoLoadPromise;

    monacoLoadPromise = new Promise(function (resolve, reject) {
      if (window.monaco && window.monaco.editor) {
        monacoLoaded = true;
        resolve();
        return;
      }

      function initWithRequire() {
        try {
          if (!window.require || !window.require.config) {
            reject(new Error("AMD loader do Monaco não disponível"));
            return;
          }
          window.require.config({
            paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" },
          });
          window.require(["vs/editor/editor.main"], function () {
            if (window.monaco && window.monaco.editor) {
              monacoLoaded = true;
              resolve();
            } else {
              reject(new Error("Monaco não inicializou corretamente"));
            }
          }, reject);
        } catch (err) {
          reject(err);
        }
      }

      if (window.require && window.require.config) {
        initWithRequire();
        return;
      }

      var existing = document.getElementById("monaco-amd-loader");
      if (existing) {
        existing.addEventListener("load", initWithRequire, { once: true });
        existing.addEventListener("error", reject, { once: true });
        return;
      }

      var script = document.createElement("script");
      script.id = "monaco-amd-loader";
      script.src = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs/loader.js";
      script.async = true;
      script.onload = initWithRequire;
      script.onerror = reject;
      document.head.appendChild(script);
    });
    return monacoLoadPromise;
  }


  // 2. Inicialização do Editor com tema Cursor
  function initMonacoEditor() {
    var container = document.getElementById("monacoContainer");
    if (!container || monacoEditor) return;

    loadMonacoAsync().then(function () {
      monacoEditor = window.monaco.editor.create(container, {
        value: "// Yui Workspace — Pronto para codar.\n",
        language: "plaintext",
        theme: "vs-dark",
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 13,
        fontFamily: "'JetBrains Mono', monospace",
        renderLineHighlight: "all",
        padding: { top: 10 },
        scrollbar: { 
            vertical: 'visible', 
            horizontal: 'visible', 
            useShadows: false, 
            verticalSliderSize: 4 
        }
      });

      // Atalho estilo Cursor: Ctrl+Enter para disparar ação principal
      monacoEditor.addCommand(window.monaco.KeyMod.CtrlCmd | window.monaco.KeyCode.Enter, function() {
        var runBtn = document.getElementById("workspaceRun");
        if (runBtn) runBtn.click();
      });

    }).catch(function (e) {
      console.warn("Falha ao carregar o Editor:", e);
    });
  }

  // 3. Efeito Visual de Atualização (Pulse)
  function triggerEditorPulse() {
    var panel = document.getElementById("workspacePanel");
    if (panel) {
      panel.classList.remove("editorPulse");
      void panel.offsetWidth; // Force reflow
      panel.classList.add("editorPulse");
      setTimeout(function () { panel.classList.remove("editorPulse"); }, 1200);
    }
  }

  // 4. Lógica de Preview Inteligente (Injeta CSS no HTML)
  window.updatePreview = function() {
    var frame = document.getElementById("workspacePreviewFrame");
    if (!frame || !monacoEditor) return;

    var content = monacoEditor.getValue();
    var model = monacoEditor.getModel();
    var lang = model ? model.getLanguageId() : "";

    if (lang === "html") {
      var cssContent = window.lastKnownCSS || ""; 
      
      var fullHtml = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <style>${cssContent}</style>
        </head>
        <body>
          ${content}
        </body>
        </html>
      `;
      
      var blob = new Blob([fullHtml], { type: 'text/html' });
      frame.src = URL.createObjectURL(blob);
      
      var emptyMsg = document.getElementById("workspacePreviewEmpty");
      if (emptyMsg) emptyMsg.style.display = "none";
      frame.style.display = "block";
    }
  };

  // 5. Mapeamento de Linguagens e Atualização Externa
  function getLangToMonaco(lang) {
    var map = { 
        js: "javascript", py: "python", ts: "typescript", 
        html: "html", css: "css", md: "markdown", json: "json" 
    };
    return map[(lang || "").toLowerCase()] || "plaintext";
  }

  window.updateEditor = function (code, lang) {
    if (!monacoEditor) {
      initMonacoEditor();
      setTimeout(() => window.updateEditor(code, lang), 500);
      return;
    }
    monacoEditor.setValue(code || "");
    var monacoLang = getLangToMonaco(lang);
    window.monaco.editor.setModelLanguage(monacoEditor.getModel(), monacoLang);
    
    if (lang === "css") window.lastKnownCSS = code;
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

  function initWorkspaceButtons() {
    if (workspaceButtonsBound) return;
  function initWorkspaceButtons() {
    if (workspaceButtonsBound) return;
  function initWorkspaceButtons() {
    if (workspaceButtonsBound) return;
  // 6. Setup de Botões e Interações
  function initWorkspaceButtons() {
    if (workspaceButtonsBound) return;
    
    var copyBtn = document.getElementById("workspaceCopy");
    if (copyBtn) {
      copyBtn.onclick = function() {
        if (!monacoEditor) return;
        navigator.clipboard.writeText(monacoEditor.getValue());
        var oldText = copyBtn.innerText;
        copyBtn.innerText = "Copiado!";
        setTimeout(() => { copyBtn.innerText = oldText; }, 2000);
      };
    }

  function initWorkspaceButtons() {
    if (workspaceButtonsBound) return;
    var tabPreview = document.querySelector('[data-tab="preview"]');
    if (tabPreview) {
      tabPreview.addEventListener("click", window.updatePreview);
    }
    
    workspaceButtonsBound = true;
  }

  window.getMonacoEditor = function () { return monacoEditor; };

  window.initYuiWorkspace = function () {
    initWorkspaceButtons();
    initMonacoEditor();
  };

  // Inicialização Automática
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", window.initYuiWorkspace);
  } else {
    window.initYuiWorkspace();
  }
})();