/**
 * Painel Admin — logs, usuários, estatísticas.
 * Requer ADMIN_EMAILS ou ADMIN_USER_IDS configurados no servidor.
 */
(function () {
  "use strict";

  function apiUrl(path) {
    return (path || "").charAt(0) === "/" ? path : "/" + path;
  }

  function getUserId() {
    if (window.USER_ID) return window.USER_ID;
    try {
      var stored = localStorage.getItem("yui_user");
      if (stored) {
        var u = JSON.parse(stored);
        return (u && u.id) ? u.id : "";
      }
    } catch (e) {}
    return "";
  }

  function getEmail() {
    try {
      var stored = localStorage.getItem("yui_user");
      if (stored) {
        var u = JSON.parse(stored);
        return (u && u.email) ? u.email : "";
      }
    } catch (e) {}
    return "";
  }

  function adminFetch(path, opts) {
    var uid = getUserId();
    if (!uid) return Promise.reject(new Error("Faça login para acessar o admin"));
    var url = apiUrl(path);
    var sep = url.indexOf("?") >= 0 ? "&" : "?";
    url += sep + "user_id=" + encodeURIComponent(uid);
    return fetch(url, opts || {}).then(function (r) { return r.json(); });
  }

  function adminPost(path, body) {
    var uid = getUserId();
    var payload = Object.assign({}, body || {}, { user_id: uid });
    return fetch(apiUrl(path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) { return r.json(); });
  }

  function adminDelete(path) {
    var uid = getUserId();
    var url = apiUrl(path) + (path.indexOf("?") >= 0 ? "&" : "?") + "user_id=" + encodeURIComponent(uid);
    return fetch(url, { method: "DELETE" }).then(function (r) { return r.json(); });
  }

  function setAdminStatus(text, ok) {
    var el = document.getElementById("adminStatus");
    if (el) {
      el.textContent = text || "";
      el.className = "adminStatus " + (ok ? "adminOk" : "adminErr");
    }
  }

  function loadLogs() {
    var pre = document.getElementById("adminLogsContent");
    if (!pre) return;
    pre.textContent = "Carregando...";
    adminFetch("/api/admin/logs?lines=300")
      .then(function (data) {
        if (data.ok && data.lines && data.lines.length) {
          pre.textContent = data.lines.join("");
          pre.scrollTop = pre.scrollHeight;
        } else {
          pre.textContent = data.message || "Nenhum log ou arquivo não existe.";
        }
      })
      .catch(function (e) {
        pre.textContent = "Erro: " + (e.message || String(e));
      });
  }

  function clearLogs() {
    if (!confirm("Limpar todo o conteúdo do arquivo de log?")) return;
    adminDelete("/api/admin/logs")
      .then(function (data) {
        if (data.ok) {
          setAdminStatus("Log limpo", true);
          loadLogs();
        } else {
          setAdminStatus(data.error || "Erro", false);
        }
      })
      .catch(function (e) {
        setAdminStatus("Erro: " + (e.message || String(e)), false);
      });
  }

  function loadUsers() {
    var div = document.getElementById("adminUsersList");
    if (!div) return;
    div.innerHTML = "Carregando...";
    adminFetch("/api/admin/users")
      .then(function (data) {
        if (!data.ok) {
          div.innerHTML = "<div class='adminError'>" + (data.error || "Erro") + "</div>";
          return;
        }
        var users = data.users || [];
        if (users.length === 0) {
          div.innerHTML = "<div class='adminEmpty'>Nenhum usuário encontrado.</div>";
          return;
        }
        var html = "<table class='adminTable'><thead><tr><th>ID</th><th>Email</th><th>Chats</th></tr></thead><tbody>";
        users.forEach(function (u) {
          html += "<tr><td class='adminTdId'>" + (u.id || "—").toString().slice(0, 8) + "…</td><td>" + (u.email || "—") + "</td><td>" + (u.chats_count || 0) + "</td></tr>";
        });
        html += "</tbody></table>";
        div.innerHTML = html;
      })
      .catch(function (e) {
        div.innerHTML = "<div class='adminError'>Erro: " + (e.message || String(e)) + "</div>";
      });
  }

  function loadStats() {
    var div = document.getElementById("adminStatsContent");
    if (!div) return;
    div.innerHTML = "Carregando...";
    adminFetch("/api/admin/stats")
      .then(function (data) {
        if (!data.ok) {
          div.innerHTML = "<div class='adminError'>" + (data.error || "Erro") + "</div>";
          return;
        }
        var s = data.stats || {};
        div.innerHTML = "<div class='adminStatsGrid'>" +
          "<div class='adminStatCard'><span class='adminStatValue'>" + (s.users || 0) + "</span><span class='adminStatLabel'>Usuários</span></div>" +
          "<div class='adminStatCard'><span class='adminStatValue'>" + (s.chats || 0) + "</span><span class='adminStatLabel'>Chats</span></div>" +
          "<div class='adminStatCard'><span class='adminStatValue'>" + (s.messages || 0) + "</span><span class='adminStatLabel'>Mensagens</span></div>" +
          "</div>";
      })
      .catch(function (e) {
        div.innerHTML = "<div class='adminError'>Erro: " + (e.message || String(e)) + "</div>";
      });
  }

  function checkAdminAndInit() {
    var uid = getUserId();
    if (!uid) {
      setAdminStatus("Faça login", false);
      return;
    }
    adminFetch("/api/admin/check")
      .then(function (data) {
        if (data.ok && data.admin) {
          setAdminStatus("Admin", true);
          loadLogs();
          document.querySelectorAll(".adminTab, .adminTabContent").forEach(function (el) { el.style.display = ""; });
        } else {
          setAdminStatus("Acesso negado", false);
          var panel = document.getElementById("adminPanel");
          if (panel) {
            var wrap = panel.querySelector(".adminTabs");
            if (wrap) wrap.style.display = "none";
            var logsEl = document.getElementById("adminTabLogs");
            var usersEl = document.getElementById("adminTabUsers");
            var statsEl = document.getElementById("adminTabStats");
            if (logsEl) logsEl.innerHTML = "<div class='adminError'>Apenas administradores podem acessar. Configure ADMIN_EMAILS ou ADMIN_USER_IDS no servidor.</div>";
            if (usersEl) usersEl.innerHTML = "";
            if (statsEl) statsEl.innerHTML = "";
          }
        }
      })
      .catch(function (e) {
        setAdminStatus("Erro: " + (e.message || String(e)), false);
      });
  }

  function initAdminTabs() {
    var tabs = document.querySelectorAll(".adminTab[data-admin-tab]");
    var contents = document.querySelectorAll(".adminTabContent");
    function switchAdminTab(tab) {
      var key = tab.getAttribute("data-admin-tab") || "";
      var targetId = "adminTab" + key.charAt(0).toUpperCase() + key.slice(1);
      tabs.forEach(function (t) { t.classList.remove("active"); });
      contents.forEach(function (c) {
        c.classList.remove("active");
        c.style.display = "none";
      });
      tab.classList.add("active");
      var target = document.getElementById(targetId);
      if (target) {
        target.classList.add("active");
        target.style.display = "block";
        if (key === "logs") loadLogs();
        else if (key === "users") loadUsers();
        else if (key === "stats") loadStats();
      }
    }
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () { switchAdminTab(tab); });
    });
  }

  function init() {
    initAdminTabs();
    var logsRefresh = document.getElementById("adminLogsRefresh");
    var logsClear = document.getElementById("adminLogsClear");
    var usersRefresh = document.getElementById("adminUsersRefresh");
    var statsRefresh = document.getElementById("adminStatsRefresh");
    if (logsRefresh) logsRefresh.addEventListener("click", loadLogs);
    if (logsClear) logsClear.addEventListener("click", clearLogs);
    if (usersRefresh) usersRefresh.addEventListener("click", loadUsers);
    if (statsRefresh) statsRefresh.addEventListener("click", loadStats);

    var adminTabEl = document.querySelector('.sidebarTab[data-sidebar-tab="admin"]');
    if (adminTabEl) {
      adminTabEl.addEventListener("click", function () {
        setTimeout(checkAdminAndInit, 100);
      });
    }
    var currentTab = document.querySelector(".sidebarTabContent#sidebarTabAdmin");
    if (currentTab && currentTab.classList.contains("active")) {
      checkAdminAndInit();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
