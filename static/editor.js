/**
 * YUI Workspace — Monaco Editor & Smart Preview
 * Estilo Cursor IDE com injeção automática de CSS e efeitos visuais.
 */
(function () {
  "use strict";

  var monacoEditor = null;
  var monacoLoaded = false;
  var monacoLoadPromise = null;
  var workspaceButtonsBound = false;

  // 1. Carregamento Assíncrono do Monaco (Evita travamentos no Zeabur)
  function loadMonacoAsync() {
    if (monacoLoaded) return Promise.resolve();
    if (monacoLoadPromise) return monacoLoadPromise;

    monacoLoadPromise = new Promise(function (resolve, reject) {
      if (window.monaco && window.monaco.editor) {
        monacoLoaded = true;
        resolve();
        return;
      }
      var script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/@monaco-editor/loader@1.7.0/lib/umd/monaco-loader.min.js";
      script.async = true;
      script.onload = function () {
        var loaderFn = window.monaco_loader || window.monacoLoader || window.loader;
        if (!loaderFn || typeof loaderFn.init !== "function") {
          reject(new Error("Monaco loader não carregou"));
          return;
        }
        loaderFn.init().then(function (monaco) {
          window.monaco = monaco;
          monacoLoaded = true;
          resolve();
        }).catch(reject);
      };
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

    var tabPreview = document.querySelector('[data-tab="preview"]');
    if (tabPreview) {
      tabPreview.addEventListener("click", window.updatePreview);
    }
    
    workspaceButtonsBound = true;
  }

  window.initYuiWorkspace = function () {
    initWorkspaceButtons();
    initMonacoEditor();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", window.initYuiWorkspace);
  } else {
    window.initYuiWorkspace();
  }
})();