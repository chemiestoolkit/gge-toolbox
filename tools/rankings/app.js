/* Player & Alliance Rankings — public tool over the gge-tracker.com API.
   Server picked via the `gge-server` header. Data credit: gge-tracker.com */
(function () {
  "use strict";

  const API = "https://api.gge-tracker.com/api/v1/";
  const SERVERS = ["AU1","INT1","INT2","INT3","DE1","FR1","GB1","US1","BR1","ES1","ES2","IT1","TR1","NL1","HU1","HU2","PL1","PT1","CZ1","SK1","SKN1","RU1","RO1","BG1","GR1","JP1","IN1","CN1","SA1","AE1","EG1","ARAB1","ASIA","HANT1","WORLD1","WORLD2","GLOBAL"];

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
  const num = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString());
  const ago = (iso) => {
    if (!iso) return "—";
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 3600) return Math.max(1, Math.round(s / 60)) + "m";
    if (s < 86400) return Math.round(s / 3600) + "h";
    return Math.round(s / 86400) + "d";
  };
  const stale = (iso) => iso && (Date.now() - new Date(iso).getTime()) > 14 * 86400 * 1000;

  function server() { return localStorage.getItem("rk_server") || "AU1"; }
  async function api(path, params) {
    const qs = params ? "?" + Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => encodeURIComponent(k) + "=" + encodeURIComponent(v)).join("&") : "";
    const r = await fetch(API + path + qs, { headers: { "gge-server": server() } });
    if (!r.ok) { let m = "HTTP " + r.status; try { m = (await r.json()).error || m; } catch (e) {} throw new Error(m); }
    return r.json();
  }

  // server selector
  const srv = $("server");
  SERVERS.forEach((s) => { const o = document.createElement("option"); o.value = s; o.textContent = s; if (s === server()) o.selected = true; srv.appendChild(o); });
  srv.addEventListener("change", () => { localStorage.setItem("rk_server", srv.value); page = 1; load(); });

  let mode = "players", page = 1, totalPages = 1;
  let orderBy = "might_current", orderType = "DESC";

  const PLAYER_COLS = [
    { key: "player_name",     label: "Player",   cls: "nm" },
    { key: "alliance_name",   label: "Alliance" },
    { key: "level",           label: "Lvl",      cls: "r", sort: "level" },
    { key: "legendary_level", label: "Leg.",     cls: "r" },
    { key: "might_current",   label: "Might",    cls: "r", sort: "might_current", num: true },
    { key: "loot_current",    label: "Loot",     cls: "r", sort: "loot_current",  num: true },
    { key: "current_fame",    label: "Glory",    cls: "r", sort: "current_fame",  num: true },
    { key: "honor",           label: "Honour",   cls: "r", sort: "honor",         num: true },
    { key: "updated_at",      label: "Updated",  cls: "r", upd: true },
  ];
  const ALLIANCE_COLS = [
    { key: "alliance_name", label: "Alliance", cls: "nm" },
    { key: "player_count",  label: "Members",  cls: "r" },
    { key: "might_current", label: "Might",    cls: "r", sort: "might_current", num: true },
    { key: "loot_current",  label: "Loot",     cls: "r", sort: "loot_current",  num: true },
    { key: "current_fame",  label: "Glory",    cls: "r", sort: "current_fame",  num: true },
    { key: "highest_fame",  label: "Best glory", cls: "r", num: true },
  ];

  async function load() {
    const status = $("status");
    status.textContent = "Loading…"; status.className = "rk-status";
    try {
      let rows, cols;
      if (mode === "players") {
        const params = { page, orderBy, orderType };
        const fa = $("f-alliance").value.trim(), ml = $("f-minlevel").value.trim();
        if (fa) params.alliance = fa;
        if (ml) params.minLevel = ml;
        const d = await api("players", params);
        rows = d.players || []; cols = PLAYER_COLS;
        totalPages = d.pagination ? d.pagination.total_pages : 1;
        status.textContent = d.pagination ? num(d.pagination.total_items_count) + " players on " + server() : "";
      } else {
        const d = await api("alliances", { page, orderBy, orderType });
        rows = d.alliances || []; cols = ALLIANCE_COLS;
        totalPages = d.pagination ? d.pagination.total_pages : 1;
        status.textContent = d.pagination ? num(d.pagination.total_items_count) + " alliances on " + server() : "";
      }
      render(rows, cols);
      $("pageinfo").textContent = "Page " + page + " / " + totalPages;
    } catch (e) {
      status.textContent = "Error: " + e.message; status.className = "rk-status err";
    }
  }

  function render(rows, cols) {
    const tbl = $("tbl");
    tbl.innerHTML = "<thead><tr>" + cols.map((c) =>
      '<th class="' + (c.cls || "") + (c.sort ? " sortable" : "") + '" data-sort="' + (c.sort || "") + '">' +
      c.label + (c.sort === orderBy ? (orderType === "DESC" ? " ↓" : " ↑") : "") + "</th>").join("") + "</tr></thead>";
    const tb = document.createElement("tbody");
    rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = cols.map((c) => {
        if (c.upd) return '<td class="r ' + (stale(r[c.key]) ? "stale" : "") + '" title="' + esc(r[c.key] || "") + '">' + ago(r[c.key]) + "</td>";
        const v = r[c.key];
        return '<td class="' + (c.cls || "") + '">' + (c.num ? num(v) : esc(v ?? "—")) + "</td>";
      }).join("");
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
    tbl.querySelectorAll("th.sortable").forEach((th) => th.addEventListener("click", () => {
      const s = th.dataset.sort; if (!s) return;
      if (orderBy === s) orderType = orderType === "DESC" ? "ASC" : "DESC";
      else { orderBy = s; orderType = "DESC"; }
      page = 1; load();
    }));
  }

  $("tab-players").addEventListener("click", function () {
    mode = "players"; page = 1; orderBy = "might_current";
    this.className = "rk-btn"; $("tab-alliances").className = "rk-btn ghost"; load();
  });
  $("tab-alliances").addEventListener("click", function () {
    mode = "alliances"; page = 1; orderBy = "might_current";
    this.className = "rk-btn"; $("tab-players").className = "rk-btn ghost"; load();
  });
  $("apply").addEventListener("click", () => { page = 1; load(); });
  $("prev").addEventListener("click", () => { if (page > 1) { page--; load(); } });
  $("next").addEventListener("click", () => { if (page < totalPages) { page++; load(); } });

  load();
})();
