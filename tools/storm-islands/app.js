/* Storm Islands Rankings — public tool over gge-tracker.com's snapshot DB
   (api.gge-tracker.com, keyed by server code via the `gge-server` header). The
   live game protocol doesn't expose the aquamarine breakdown, so this is the
   only source for cargo points + per-source sub-scores. Data: gge-tracker.com */
(function () {
  "use strict";

  const API = "https://api.gge-tracker.com/api/v1/";
  const SERVERS = ["AU1","INT1","INT2","INT3","DE1","FR1","GB1","US1","BR1","ES1","ES2","IT1","TR1","NL1","HU1","HU2","PL1","PT1","CZ1","SK1","SKN1","RU1","RO1","BG1","GR1","JP1","IN1","CN1","SA1","AE1","EG1","ARAB1","ASIA","HANT1","WORLD1","WORLD2","GLOBAL"];

  // Aquamarine metric ids -> column label (100 = cargo points = the score).
  const COLS = [
    { m: "100", label: "Cargo pts" }, { m: "15", label: "Aqua total" },
    { m: "16", label: "Res. isles" }, { m: "17", label: "Storm forts" },
    { m: "18", label: "PvP won" },    { m: "19", label: "Spent" },
    { m: "20", label: "PvP lost" },
  ];

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
  const num = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString());

  function server() { return localStorage.getItem("storm_server") || "AU1"; }

  let page = 1, totalPages = 1, searchName = "";

  async function load() {
    const status = $("status");
    status.textContent = "Loading…"; status.className = "rk-status";
    const qs = "page=" + page + "&order_by=100&order_dir=desc" +
      (searchName ? "&player_name=" + encodeURIComponent(searchName) : "");
    try {
      const r = await fetch(API + "stormy-isles?" + qs, { headers: { "gge-server": server() } });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const d = await r.json();
      const rows = d.players || [];
      const pg = d.pagination || {};
      totalPages = pg.total_pages || 1;
      render(rows);
      $("pageinfo").textContent = rows.length ? "Page " + (pg.current_page || page) + " / " + totalPages : "";
      status.textContent = "🌊 " + server() + " · " + num(pg.total_items_count || rows.length) + " ranked" +
        (searchName ? " matching “" + searchName + "”" : "") +
        (d.snapshot_date ? " · snapshot " + d.snapshot_date : "");
      if (!rows.length) status.textContent = "No Storm Islands scores" + (searchName ? " for “" + searchName + "”" : "") + " on " + server() + ".";
    } catch (e) {
      status.textContent = "Could not load Storm Islands scores — " + e.message;
      status.className = "rk-status err"; $("tbl").innerHTML = ""; $("pageinfo").textContent = "";
    }
  }

  function render(rows) {
    const tbl = $("tbl");
    tbl.innerHTML = "<thead><tr>" +
      '<th class="r">#</th><th>Player</th><th>Level</th><th>Alliance</th>' +
      COLS.map((c) => '<th class="r">' + c.label + "</th>").join("") +
      "</tr></thead>";
    const tb = document.createElement("tbody");
    rows.forEach((p) => {
      const m = p.metrics || {};
      const lvl = p.legendary_level ? esc(p.level) + " / " + esc(p.legendary_level) : esc(p.level);
      const tr = document.createElement("tr");
      tr.innerHTML =
        '<td class="r">' + num(p.rank) + '</td>' +
        '<td class="nm">' + esc(p.player_name || "?") + "</td>" +
        "<td>" + lvl + "</td>" +
        "<td>" + esc(p.alliance_name || "—") + "</td>" +
        COLS.map((c) => '<td class="r">' + num(m[c.m]) + "</td>").join("");
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
  }

  // ---- wiring ----
  const srv = $("server");
  SERVERS.forEach((s) => { const o = document.createElement("option"); o.value = s; o.textContent = s; if (s === server()) o.selected = true; srv.appendChild(o); });
  srv.addEventListener("change", () => { localStorage.setItem("storm_server", srv.value); page = 1; load(); });

  function doSearch() { searchName = $("q").value.trim(); page = 1; load(); }
  $("go").addEventListener("click", doSearch);
  $("q").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
  $("clear").addEventListener("click", () => { $("q").value = ""; searchName = ""; page = 1; load(); });

  $("prev").addEventListener("click", () => { if (page > 1) { page--; load(); } });
  $("next").addEventListener("click", () => { if (page < totalPages) { page++; load(); } });

  load();
})();
