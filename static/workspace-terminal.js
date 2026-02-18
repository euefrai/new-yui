/**
 * YUI Workspace — Terminal Xterm.js conectado ao shell do servidor
 */
(function () {
  "use strict";

  var term = null;
  var fitAddon = null;
  var ws = null;
  var container = null;

  function getWsUrl() {
    var loc = window.location;
    var protocol = loc.protocol === "https:" ? "wss:" : "ws:";
    return protocol + "//" + loc.host + "/ws/terminal";
  }

  function initTerminal() {
    container = document.getElementById("workspaceTerminal");
    if (!container || !window.Terminal) return;
    if (term) return;
    term = new window.Terminal({
      cursorBlink: true,
      theme: {
        background: "#1a1a1e",
        foreground: "#e8e8ec",
        cursor: "#00f2ff",
        black: "#1a1a1e",
        red: "#ff6b6b",
        green: "#69db7c",
        yellow: "#ffd43b",
        blue: "#74c0fc",
        magenta: "#da77f2",
        cyan: "#00f2ff",
        white: "#e8e8ec",
      },
      fontSize: 13,
      fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
    });
    try {
      if (window.FitAddon) {
        fitAddon = new window.FitAddon.FitAddon();
        term.loadAddon(fitAddon);
      }
    } catch (e) {}
    term.open(container);
    if (fitAddon) fitAddon.fit();
    term.writeln("Conectando ao terminal...");
    connect();
    container.addEventListener("click", function () {
      if (term) term.focus();
    });
  }

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    try {
      ws = new WebSocket(getWsUrl());
      ws.binaryType = "arraybuffer";
      ws.onopen = function () {
        term.clear();
        term.writeln("Terminal conectado. Cwd: sandbox/");
      };
      ws.onmessage = function (ev) {
        var str = typeof ev.data === "string" ? ev.data : new TextDecoder().decode(ev.data);
        term.write(str);
      };
      ws.onclose = function () {
        term.writeln("\r\n\r\nTerminal desconectado. Recarregue o Workspace para reconectar.");
      };
      ws.onerror = function () {
        term.writeln("\r\nErro de conexão. O terminal pode não estar disponível neste ambiente.");
      };
      term.onData(function (data) {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(data);
      });
    } catch (e) {
      term.writeln("\r\nErro ao conectar: " + (e.message || String(e)));
    }
  }

  function disposeTerminal() {
    if (ws) {
      ws.close();
      ws = null;
    }
    if (term) {
      term.dispose();
      term = null;
    }
  }

  function fitTerminalSoon() {
    if (term && fitAddon) setTimeout(function () { fitAddon.fit(); }, 100);
  }

  function toggleTerminal() {
    var wrap = document.getElementById("workspaceTerminalWrap");
    var toggleBtn = document.getElementById("workspaceTerminalToggle");
    if (!wrap) return;
    wrap.classList.toggle("collapsed");
    if (!wrap.classList.contains("collapsed")) wrap.classList.remove("expanded");
    if (toggleBtn) toggleBtn.textContent = wrap.classList.contains("collapsed") ? "▲" : "▼";
    if (!wrap.classList.contains("collapsed")) {
      fitTerminalSoon();
      if (term) setTimeout(function () { term.focus(); }, 150);
    }
  }

  function toggleTerminalExpand() {
    var wrap = document.getElementById("workspaceTerminalWrap");
    var expandBtn = document.getElementById("workspaceTerminalExpand");
    if (!wrap) return;
    wrap.classList.remove("collapsed");
    wrap.classList.toggle("expanded");
    if (expandBtn) {
      expandBtn.textContent = wrap.classList.contains("expanded") ? "🗗" : "⤢";
      expandBtn.title = wrap.classList.contains("expanded") ? "Restaurar tamanho do terminal" : "Ampliar terminal";
    }
    fitTerminalSoon();
  }

  function onWorkspaceVisible() {
    var panel = document.getElementById("workspacePanel");
    if (!panel || panel.offsetParent === null) return;
    if (!term) {
      if (window.Terminal) {
        container = document.getElementById("workspaceTerminal");
        if (container) initTerminal();
      } else {
        setTimeout(onWorkspaceVisible, 300);
      }
    } else if (fitAddon) fitTerminalSoon();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var toggleBtn = document.getElementById("workspaceTerminalToggle");
    var expandBtn = document.getElementById("workspaceTerminalExpand");
    if (toggleBtn) toggleBtn.addEventListener("click", toggleTerminal);
    if (expandBtn) expandBtn.addEventListener("click", toggleTerminalExpand);
    var observer = new MutationObserver(function () { onWorkspaceVisible(); });
    var mainSplit = document.getElementById("mainSplit");
    if (mainSplit) observer.observe(mainSplit, { attributes: true, attributeFilter: ["class"] });
    var toggleWorkspace = document.getElementById("toggleWorkspace");
    if (toggleWorkspace) {
      toggleWorkspace.addEventListener("click", function () {
        setTimeout(onWorkspaceVisible, 300);
      });
    }
    window.addEventListener("resize", function () { if (term && fitAddon) fitAddon.fit(); });
    setTimeout(onWorkspaceVisible, 500);
  });
})();
