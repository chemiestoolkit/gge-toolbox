/* Player & Alliance Rankings — public tool over the GAME'S OWN highscore lists,
   served by danadum's empire-api (empire-api.fly.dev), the same live source the
   VIP Live Event Rankings use. This is the real in-game leaderboard — it tops out
   at the genuine #1 (e.g. AU1 Hards161 ~495M), unlike third-party crawl indexes
   which miss most large accounts. Data credit: danadum / Goodgame Empire. */
(function () {
  "use strict";

  const API = "https://empire-api.fly.dev";

  // Zone code -> friendly name (danadum server ids).
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

  // Level brackets for the per-level player lists (LID values).
  const BRACKETS = [
    { id: 1, label: "Level 1–19" }, { id: 2, label: "Level 20–29" },
    { id: 3, label: "Level 30–39" }, { id: 4, label: "Level 40–49" },
    { id: 5, label: "Level 50–69" }, { id: 6, label: "Level 70" },
  ];

  // The leaderboards we expose. `lt` = list type, `kind` player|alliance,
  // `brackets` = uses level brackets (LID 1–6, default 6 = level 70).
  const CATS = [
    { key: "might",     label: "Player · Might",       lt: 6,  kind: "player",   brackets: true,  score: "Might" },
    { key: "honor",     label: "Player · Honour",      lt: 5,  kind: "player",   brackets: true,  score: "Honour" },
    { key: "legend",    label: "Player · Legend lvl",  lt: 7,  kind: "player",   brackets: false, lid: 6, score: "Legend lvl" },
    { key: "achiev",    label: "Player · Achievement", lt: 1,  kind: "player",   brackets: true,  score: "Points" },
    { key: "amight",    label: "Alliance · Might",     lt: 11, kind: "alliance", brackets: false, lid: 1, score: "Might" },
    { key: "ahonor",    label: "Alliance · Honour",    lt: 10, kind: "alliance", brackets: false, lid: 1, score: "Honour" },
  ];

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
  const num = (v) => (v == null || v === "" ? "—" : Number(v).toLocaleString());

  function server() { return localStorage.getItem("rk_server") || "EmpireEx_22"; }
  function curCat() { return CATS.find((c) => c.key === ($("cat").value)) || CATS[0]; }
  function curLid() {
    const c = curCat();
    if (!c.brackets) return c.lid;
    return Number($("bracket").value || 6);
  }

  // Call the game's highscore command. `sv` is the search value: a rank (centres
  // the window) or a name (jumps to that entry, FR = its rank). Retries once —
  // the game occasionally returns an error before the list is warm.
  async function hgh(lt, lid, sv) {
    const inner = '"LT":' + lt + (lid != null ? ',"LID":' + lid : "") + ',"SV":"' + String(sv).replace(/"/g, "") + '"';
    const url = API + "/" + server() + "/hgh/" + encodeURIComponent(inner);
    for (let attempt = 0; attempt < 2; attempt++) {
      let j = null;
      try { j = await (await fetch(url)).json(); } catch (e) {}
      if (j && (j.return_code === 0 || j.return_code === "0") && j.content) return j.content;
      if (attempt === 0) await new Promise((r) => setTimeout(r, 600));
    }
    throw new Error("No leaderboard returned — this list may be empty for this server/bracket.");
  }

  let page = 1, maxRank = 1, mode = "rank", searchName = "";

  async function load() {
    const status = $("status");
    const c = curCat();
    status.textContent = "Loading…"; status.className = "rk-status";
    // bracket picker visibility
    $("bracket").style.display = c.brackets ? "" : "none";
    try {
      let content, sv;
      if (mode === "name" && searchName) {
        content = await hgh(c.lt, curLid(), searchName);
        // re-centre paging on where the player landed
        const fr = content.FR || (content.L && content.L.length ? content.L[0][0] : 1);
        page = Math.max(1, Math.ceil(fr / 10));
      } else {
        sv = page * 10 - 5;            // window of 10 centred so page N == ranks (N-1)*10+1 .. N*10
        content = await hgh(c.lt, curLid(), sv);
      }
      maxRank = content.LR || maxRank;
      const rows = content.L || [];
      render(rows, c, searchName && mode === "name" ? (content.FR || null) : null);
      const totalPages = Math.max(1, Math.ceil(maxRank / 10));
      $("pageinfo").textContent = rows.length
        ? "Ranks " + num(rows[0][0]) + "–" + num(rows[rows.length - 1][0]) + " · page " + page + " / ~" + totalPages
        : "";
      status.textContent = c.label + " — " + SERVERS[server()] +
        (c.brackets ? " · " + (BRACKETS.find((b) => b.id === curLid()) || {}).label : "") +
        " · top tracked rank ~" + num(maxRank);
    } catch (e) {
      status.textContent = e.message; status.className = "rk-status err";
      $("tbl").innerHTML = ""; $("pageinfo").textContent = "";
    }
  }

  function render(rows, c, foundRank) {
    const tbl = $("tbl");
    const player = c.kind === "player";
    const heads = player
      ? ["#", "Player", "Level", "Alliance", c.score]
      : ["#", "Alliance", "Members", c.score];
    tbl.innerHTML = "<thead><tr>" +
      heads.map((h, i) => '<th class="' + (i === 0 || i === heads.length - 1 || (!player && i === 2) ? "r" : "") + '">' + h + "</th>").join("") +
      "</tr></thead>";
    const tb = document.createElement("tbody");
    rows.forEach((row) => {
      const [rank, score, info] = row;
      const tr = document.createElement("tr");
      if (foundRank && rank === foundRank) tr.className = "hit";
      if (player) {
        // info is an object: N name, L level, LL legendary level, AN alliance
        const lvl = info.LL ? esc(info.L) + " / " + esc(info.LL) : esc(info.L);
        tr.innerHTML =
          '<td class="r">' + num(rank) + '</td>' +
          '<td class="nm">' + esc(info.N || "?") + "</td>" +
          '<td>' + lvl + "</td>" +
          "<td>" + esc(info.AN || "—") + "</td>" +
          '<td class="r">' + num(score) + "</td>";
      } else {
        // info is an array: [allianceId, name, members, fame]
        tr.innerHTML =
          '<td class="r">' + num(rank) + '</td>' +
          '<td class="nm">' + esc(info[1] || "?") + "</td>" +
          '<td class="r">' + num(info[2]) + "</td>" +
          '<td class="r">' + num(score) + "</td>";
      }
      tb.appendChild(tr);
    });
    tbl.appendChild(tb);
  }

  // ---- wiring ----
  const srv = $("server");
  Object.entries(SERVERS).forEach(([z, n]) => {
    const o = document.createElement("option"); o.value = z; o.textContent = n;
    if (z === server()) o.selected = true; srv.appendChild(o);
  });
  srv.addEventListener("change", () => { localStorage.setItem("rk_server", srv.value); page = 1; mode = "rank"; load(); });

  CATS.forEach((c) => { const o = document.createElement("option"); o.value = c.key; o.textContent = c.label; $("cat").appendChild(o); });
  $("cat").value = "might";
  $("cat").addEventListener("change", () => { page = 1; mode = "rank"; searchName = ""; $("q").value = ""; load(); });

  BRACKETS.slice().reverse().forEach((b) => { const o = document.createElement("option"); o.value = b.id; o.textContent = b.label; $("bracket").appendChild(o); });
  $("bracket").value = 6;
  $("bracket").addEventListener("change", () => { page = 1; mode = "rank"; load(); });

  function doSearch() {
    const v = $("q").value.trim();
    if (!v) { mode = "rank"; searchName = ""; }
    else { mode = "name"; searchName = v; }
    page = 1;
    load();
  }
  $("go").addEventListener("click", doSearch);
  $("q").addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });

  $("prev").addEventListener("click", () => { if (page > 1) { page--; mode = "rank"; load(); } });
  $("next").addEventListener("click", () => { if (page * 10 < maxRank) { page++; mode = "rank"; load(); } });

  load();
})();
