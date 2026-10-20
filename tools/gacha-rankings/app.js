/* Gacha Rankings — the game's own highscore lists for the gacha events
   (HighscoreConst DECO_GACHA_EVENT 80 .. CARNIVAL_GACHA_EVENT 88; the Halloween
   Banquet is 86), served by danadum's empire-api (empire-api.fly.dev) like the
   Player & Alliance Rankings. In the game the gacha window only shows your own
   rank (the gde reply's OR); hgh with the event's list type gives the whole list.
   The api answers 8 rows per call: ranks SV-3 .. SV+4. Data credit: danadum /
   Goodgame Empire. */
(function () {
  "use strict";

  const API = "https://empire-api.fly.dev";
  const PAGE = 8;                       // rows per api call
  const REFRESH_MS = 60000;

  // Zone code -> friendly name (danadum server ids), as in ../rankings/app.js.
  const SERVERS = {
    "EmpireEx_22": "Australia (AU1)", "EmpireEx": "International 1", "EmpireEx_7": "International 2",
    "EmpireEx_43": "International 3", "EmpireEx_46": "World 1", "EmpireEx_49": "World 2",
    "EmpireEx_2": "Germany", "EmpireEx_3": "France", "EmpireEx_19": "Great Britain",
    "EmpireEx_21": "USA", "EmpireEx_20": "Brazil", "EmpireEx_8": "Spain", "EmpireEx_38": "Spain 2",
    "EmpireEx_9": "Italy", "EmpireEx_10": "Turkey", "EmpireEx_11": "Netherlands",
    "EmpireEx_12": "Hungary", "EmpireEx_17": "Hungary 2", "EmpireEx_5": "Poland",
    "EmpireEx_6": "Portuguese", "EmpireEx_4": "Czechia", "EmpireEx_18": "Slovakia",
    "EmpireEx_13": "Scandinavia", "EmpireEx_14": "Russia", "EmpireEx_15": "Romania",
    "EmpireEx_16": "Bulgaria", "EmpireEx_28": "Greece", "EmpireEx_29": "Lithuania",
    "EmpireEx_24": "Japan", "EmpireEx_26": "India", "EmpireEx_27": "China",
    "EmpireEx_25": "Hispanic", "EmpireEx_32": "Saudi Arabia", "EmpireEx_33": "UAE",
    "EmpireEx_34": "Egypt", "EmpireEx_35": "Arab", "EmpireEx_36": "Asia", "EmpireEx_37": "HANT",
  };

  // The gacha leaderboards: list type -> the game's own event title (en.json
  // title_<X>Gacha). `months`: when it usually runs, to pick the default.
  const EVENTS = [
    { lt: 86, name: "Halloween Banquet",            months: [9, 10] },
    { lt: 87, name: "Midnight Market",              months: [11] },
    { lt: 81, name: "The Enchanted Snowglobe",      months: [12, 1] },
    { lt: 88, name: "Carnival of Masks",            months: [2, 3] },
    { lt: 82, name: "Summoning of the Hollow Moon", months: [3, 4] },
    { lt: 85, name: "King's Banquet",               months: [5, 6] },
    { lt: 83, name: "Sands of Fortune",             months: [7, 8] },
    { lt: 80, name: "Decoration Gacha",             months: [] },
  ];
  const LEAGUES = [1, 2, 3, 4, 5, 6];

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const num = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString());
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} },
  };

  function server() { return store.get("gr_server", store.get("rk_server", "EmpireEx_22")); }
  function lt() { return Number($("event").value); }
  function lid() { return Number($("league").value || 1); }
  function me() { return store.get("gr_me", ""); }
  const sameName = (a, b) => String(a || "").toLowerCase() === String(b || "").toLowerCase();

  // The game's highscore command. `sv`: a rank (the window around it) or a
  // name (the window around that player; FR = their rank). Retried once.
  async function hgh(list, league, sv) {
    const inner = '"LT":' + list + ',"LID":' + league + ',"SV":"' + String(sv).replace(/"/g, "") + '"';
    const url = API + "/" + server() + "/hgh/" + encodeURIComponent(inner);
    for (let attempt = 0; attempt < 2; attempt++) {
      let j = null;
      try { j = await (await fetch(url)).json(); } catch (e) {}
      if (j && (j.return_code === 0 || j.return_code === "0") && j.content) return j.content;
      if (attempt === 0) await new Promise((r) => setTimeout(r, 600));
    }
    throw new Error("The rankings service didn't answer — try again in a moment.");
  }

  let page = 1, total = 0, mode = "page", find = "", leagues = [], timer = null, busy = false;

  // ---- the event and its leagues ------------------------------------------
  async function probeLeagues(list) {
    const res = await Promise.all(LEAGUES.map((l) =>
      hgh(list, l, "1").then((c) => [l, c.LR || 0]).catch(() => [l, 0])));
    return res.filter(([, n]) => n > 0);
  }

  async function chooseEvent() {
    // the one that usually runs this month, else the first with entries
    const month = new Date().getMonth() + 1;
    const order = EVENTS.slice().sort((a, b) =>
      (b.months.includes(month) ? 1 : 0) - (a.months.includes(month) ? 1 : 0));
    for (const ev of order) {
      const ls = await probeLeagues(ev.lt).catch(() => []);
      if (ls.length) return { ev, ls };
    }
    return { ev: order[0], ls: [] };
  }

  function fillLeagues(ls) {
    leagues = ls;
    const sel = $("league");
    sel.innerHTML = "";
    ls.forEach(([l, n]) => {
      const o = document.createElement("option");
      o.value = l; o.textContent = "League " + l + " · " + num(n) + " players";
      sel.appendChild(o);
    });
    sel.style.display = ls.length > 1 ? "" : "none";
  }

  async function openEvent(list, ls) {
    $("status").textContent = "Loading…"; $("status").className = "gr-status";
    fillLeagues(ls || await probeLeagues(list));
    page = 1; mode = "page"; find = "";
    if (!leagues.length) {
      total = 0;
      $("tbl").innerHTML = ""; $("pageinfo").textContent = ""; $("you").className = "gr-you";
      const ev = EVENTS.find((e) => e.lt === list);
      $("status").textContent = (ev ? ev.name : "This gacha") + " has no entries on " +
        (SERVERS[server()] || server()) + " right now — it may not be running.";
      return;
    }
    // your league, when your name is saved and you're in one of them
    if (me() && leagues.length > 1) {
      for (const [l] of leagues) {
        const c = await hgh(list, l, me()).catch(() => null);
        if (c && (c.L || []).some((r) => sameName((r[2] || {}).N, me()))) { $("league").value = l; break; }
      }
    }
    await load();
  }

  // ---- the list -------------------------------------------------------------
  async function load() {
    if (busy) return;
    busy = true;
    const status = $("status");
    try {
      let content;
      if (mode === "find" && find) {
        content = await hgh(lt(), lid(), find);
        page = Math.max(1, Math.ceil((content.FR || 1) / PAGE));
      } else if (mode === "all") {
        content = await loadAll();
      } else {
        content = await hgh(lt(), lid(), (page - 1) * PAGE + 4);
      }
      total = content.LR || total;
      render(content.L || [], mode === "find" ? find : null);
      const rows = content.L || [];
      $("pageinfo").textContent = rows.length
        ? (mode === "all" ? "All " + num(rows.length) + " ranks"
          : "Ranks " + num(rows[0][0]) + "–" + num(rows[rows.length - 1][0]) +
            " · page " + page + " / " + Math.max(1, Math.ceil(total / PAGE)))
        : "";
      const ev = EVENTS.find((e) => e.lt === lt());
      status.textContent = (ev ? ev.name : "Gacha") + " — " + (SERVERS[server()] || server()) +
        (leagues.length > 1 ? " · league " + lid() : "") + " · " + num(total) + " players ranked";
      status.className = "gr-status";
      await loadMe();
      $("updated").textContent = "· updated " + new Date().toLocaleTimeString();
    } catch (e) {
      status.textContent = e.message; status.className = "gr-status err";
    } finally {
      busy = false;
    }
  }

  async function loadAll() {
    // every window of 8, one after another (the api is a free community service)
    const first = await hgh(lt(), lid(), "4");
    const n = first.LR || 0;
    const rows = new Map((first.L || []).map((r) => [r[0], r]));
    for (let sv = 12; sv - 3 <= n; sv += PAGE) {
      $("status").textContent = "Loading the full list… " + Math.min(n, sv + 4) + " / " + n;
      const c = await hgh(lt(), lid(), sv);
      (c.L || []).forEach((r) => rows.set(r[0], r));
    }
    return { LR: n, L: Array.from(rows.values()).sort((a, b) => a[0] - b[0]) };
  }

  function render(rows, hit) {
    const tbl = $("tbl");
    tbl.innerHTML = '<thead><tr><th class="r">#</th><th>Player</th><th>Level</th>' +
      '<th class="al">Alliance</th><th class="r">Points</th></tr></thead>';
    const tb = document.createElement("tbody");
    rows.forEach(([rank, score, info]) => {
      info = info || {};
      const tr = document.createElement("tr");
      if (me() && sameName(info.N, me())) tr.className = "me";
      else if (hit && sameName(info.N, hit)) tr.className = "hit";
      const lvl = info.LL ? esc(info.L) + " / " + esc(info.LL) : esc(info.L);
      tr.innerHTML =
        '<td class="r">' + num(rank) + "</td>" +
        '<td class="nm">' + esc(info.N || "?") + "</td>" +
        "<td>" + lvl + "</td>" +
        '<td class="al">' + esc(info.AN || "—") + "</td>" +
        '<td class="r">' + num(score) + "</td>";
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
  }

  // ---- you ----------------------------------------------------------------------
  async function loadMe() {
    const box = $("you");
    const name = me();
    if (!name) { box.className = "gr-you"; return; }
    const c = await hgh(lt(), lid(), name).catch(() => null);
    const rows = (c && c.L) || [];
    const i = rows.findIndex((r) => sameName((r[2] || {}).N, name));
    if (i < 0) {
      box.innerHTML = '<div><div class="lbl">You</div><div class="val">' + esc(name) +
        '</div><div class="sub">not ranked in this list yet</div></div>' + forget();
      box.className = "gr-you on";
      wireForget();
      return;
    }
    const [rank, pts, info] = rows[i];
    const above = i > 0 ? rows[i - 1] : null;
    const below = i < rows.length - 1 ? rows[i + 1] : null;
    box.innerHTML =
      '<div><div class="lbl">Your rank</div><div class="big">#' + num(rank) + "</div></div>" +
      '<div><div class="lbl">' + esc((info || {}).N || name) + '</div><div class="val">' + num(pts) +
        ' points</div><div class="sub">of ' + num(c.LR) + " players</div></div>" +
      (above ? '<div><div class="lbl">To pass #' + num(above[0]) + '</div><div class="val">+' +
        num(Math.max(1, above[1] - pts + 1)) + '</div><div class="sub"><span class="who">' +
        esc((above[2] || {}).N) + "</span> · " + num(above[1]) + "</div></div>" : "") +
      (below ? '<div><div class="lbl">Lead over #' + num(below[0]) + '</div><div class="val">' +
        num(pts - below[1]) + '</div><div class="sub"><span class="who">' +
        esc((below[2] || {}).N) + "</span> · " + num(below[1]) + "</div></div>" : "") +
      forget();
    box.className = "gr-you on";
    wireForget();
  }

  function forget() {
    return '<button class="gr-btn ghost" id="forget" style="margin-left:auto">Forget name</button>';
  }

  function wireForget() {
    const b = $("forget");
    if (b) b.addEventListener("click", () => { store.set("gr_me", null); $("you").className = "gr-you"; load(); });
  }

  // ---- wiring -----------------------------------------------------------------
  const srv = $("server");
  Object.entries(SERVERS).forEach(([z, n]) => {
    const o = document.createElement("option"); o.value = z; o.textContent = n;
    if (z === server()) o.selected = true; srv.appendChild(o);
  });
  srv.addEventListener("change", () => { store.set("gr_server", srv.value); openEvent(lt()); });

  EVENTS.forEach((e) => {
    const o = document.createElement("option"); o.value = e.lt; o.textContent = e.name;
    $("event").appendChild(o);
  });
  $("event").addEventListener("change", () => openEvent(lt()));
  $("league").addEventListener("change", () => { page = 1; mode = "page"; load(); });

  function doFind() {
    const v = $("q").value.trim();
    mode = v ? "find" : "page"; find = v; if (!v) page = 1;
    load();
  }
  $("go").addEventListener("click", doFind);
  $("q").addEventListener("keydown", (e) => { if (e.key === "Enter") doFind(); });
  $("me").addEventListener("click", () => {
    const v = $("q").value.trim() || me();
    if (!v) { $("q").focus(); $("q").placeholder = "Type your name first…"; return; }
    store.set("gr_me", v);
    mode = "find"; find = v;
    load();
  });

  $("prev").addEventListener("click", () => { if (page > 1) { page--; mode = "page"; load(); } });
  $("next").addEventListener("click", () => { if (page * PAGE < total) { page++; mode = "page"; load(); } });
  $("all").addEventListener("click", () => { mode = "all"; load(); });

  function arm() {
    clearInterval(timer);
    // a full list is 15+ calls: only the page you're on (and you) refresh
    if ($("live").checked) timer = setInterval(() => { if (!document.hidden && mode !== "all") load(); }, REFRESH_MS);
  }
  $("live").addEventListener("change", arm);

  if (me()) $("q").value = me();
  $("status").textContent = "Finding the gacha that's running…";
  chooseEvent().then(({ ev, ls }) => { $("event").value = ev.lt; return openEvent(ev.lt, ls); })
    .catch((e) => { $("status").textContent = e.message; $("status").className = "gr-status err"; });
  arm();
})();
