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
        scrollbar: { vertical: 'visible', horizontal: 'visible', useShadows: false, verticalSliderSize: 4 }
      });

      // Atalho estilo Cursor: Ctrl+Enter para Executar/Sync
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
      panel.offsetHeight; // Trigger reflow para reiniciar animação
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
          <style>${cssContent}</style>
        </head>
        <body>
          ${content}
        </body>
        </html>
      `;
      
      var blob = new Blob([fullHtml], { type: 'text/html' });
      frame.src = URL.createObjectURL(blob);
      
      document.getElementById("workspacePreviewEmpty")?.style.display = "none";
      frame.style.display = "block";
    }
  };

  // 5. Mapeamento de Linguagens e Atualização Externa
  function getLangToMonaco(lang) {
    var map = { js: "javascript", py: "python", ts: "typescript", html: "html", css: "css", md: "markdown" };
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
    triggerEditorPulse(); // Feedback visual de que o código mudou
  };

  // 6. Setup de Botões e Tabs
  function initWorkspaceButtons() {
    if (workspaceButtonsBound) return;
    workspaceButtonsBound = true;

    var copyBtn = document.getElementById("workspaceCopy");
    var tabPreview = document.querySelector('[data-tab="preview"]');

    if (copyBtn) {
      copyBtn.onclick = function() {
        navigator.clipboard.writeText(monacoEditor.getValue());
        // Feedback visual no botão
        var oldText = copyBtn.innerText;
        copyBtn.innerText = "Copiado!";
        setTimeout(() => { copyBtn.innerText = oldText; }, 2000);
      };
    }
    
    if (tabPreview) {
      tabPreview.addEventListener("click", window.updatePreview);
    }
  }

  window.initYuiWorkspace = function () {
    initWorkspaceButtons();
    initMonacoEditor();
  };

  document.addEventListener("DOMContentLoaded", window.initYuiWorkspace);
})();