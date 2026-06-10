/* Chemie's VIP Corner — shared client for the gge-tracker.com public API.
   API: https://api.gge-tracker.com/api/v1/ (no auth, CORS open, server picked
   via the `gge-server` header). Docs: https://docs.gge-tracker.com
   All data credit: gge-tracker.com */
(function () {
  "use strict";

  // ---- Gate: sub-pages bounce to the lock screen if not unlocked ----
  if (localStorage.getItem("vip_unlocked_v1") !== "1") {
    location.replace("./index.html");
    return;
  }

  const API = "https://api.gge-tracker.com/api/v1/";
  const SERVERS = ["AU1","INT1","INT2","INT3","DE1","FR1","GB1","US1","BR1","ES1","ES2","IT1","TR1","NL1","HU1","HU2","PL1","PT1","CZ1","SK1","SKN1","RU1","RO1","BG1","GR1","JP1","IN1","CN1","SA1","AE1","EG1","ARAB1","ASIA","HANT1","WORLD1","WORLD2","GLOBAL"];

  function server() {
    return localStorage.getItem("vip_server") || "AU1";
  }

  async function api(path, params) {
    const qs = params
      ? "?" + Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== "")
          .map(([k, v]) => encodeURIComponent(k) + "=" + encodeURIComponent(v))
          .join("&")
      : "";
    const r = await fetch(API + path + qs, { headers: { "gge-server": server() } });
    if (!r.ok) {
      let msg = "HTTP " + r.status;
      try { msg = (await r.json()).error || msg; } catch (e) { /* keep status */ }
      throw new Error(msg);
    }
    return r.json();
  }

  /* Topbar server selector — call once per page. */
  function mountServerPicker(el) {
    const sel = document.createElement("select");
    sel.className = "vip-server-pick";
    SERVERS.forEach((s) => {
      const o = document.createElement("option");
      o.value = s; o.textContent = s;
      if (s === server()) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener("change", () => {
      localStorage.setItem("vip_server", sel.value);
      location.reload();
    });
    const wrap = document.createElement("label");
    wrap.className = "vip-server-wrap";
    wrap.innerHTML = "<span>Server</span>";
    wrap.appendChild(sel);
    el.appendChild(wrap);
  }

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const num = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString());
  const ago = (iso) => {
    if (!iso) return "—";
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 3600) return Math.max(1, Math.round(s / 60)) + "m ago";
    if (s < 86400) return Math.round(s / 3600) + "h ago";
    return Math.round(s / 86400) + "d ago";
  };
  const dur = (sec) => {
    if (sec == null || sec < 0) return "—";
    if (sec === 0) return "now";
    const h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60);
    return h ? h + "h " + m + "m" : m + "m";
  };

  window.VIP = { api, server, mountServerPicker, esc, num, ago, dur };
})();
