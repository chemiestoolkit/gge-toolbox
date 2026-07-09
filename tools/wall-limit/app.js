/* Wall & Courtyard Defence Caps calculator.
   Building courtyard-capacity tables are in-game verified (see the Courtyard
   Limits guide). Decoration bonuses load from ./data/defence-decos.json (game
   data cache) and are summed against the deco caps. */
(function () {
  "use strict";

  // [personal, alliance] courtyard troop capacity per level. Index 0 = not built.
  const BUILDINGS = {
    Keep:             { icon: "🏰", levels: [[0,0],[10000,100000],[50000,100000],[100000,100000],[150000,150000],[200000,200000],[250000,200000],[300000,200000],[350000,250000]] },
    Guardhouse:       { icon: "🛡️", levels: [[0,0],[1000,500],[2000,1000],[3000,1500],[4000,2000],[5000,2500],[6000,3000],[7000,3500]] },
    Stronghold:       { icon: "🏯", levels: [[0,0],[7500,2500],[15000,5000],[30000,10000],[45000,15000],[60000,20000]] },
    "Reinforced Vault": { icon: "🗝️", levels: [[0,0],[5000,25000],[10000,30000],[15000,35000],[20000,40000],[25000,45000],[30000,50000],[40000,60000],[50000,70000],[55000,80000],[65000,100000]] },
  };

  const $ = (id) => document.getElementById(id);
  const num = (v) => Number(v || 0).toLocaleString();
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));

  let CAPS = { personalCY: 175000, allianceCY: 150000, wallPct: 160, cyStrPct: 130 };
  let DECOS = [];
  const buildLevel = {};               // building name -> selected level (default top)
  const decoQty = {};                  // deco index -> count

  // ---- buildings UI ----
  function renderBuilds() {
    $("builds").innerHTML = Object.entries(BUILDINGS).map(([name, b]) => {
      const lv = buildLevel[name];
      const max = b.levels.length - 1;
      const [p, a] = b.levels[lv];
      const opts = b.levels.map((_, i) =>
        '<option value="' + i + '"' + (i === lv ? " selected" : "") + ">" + (i === 0 ? "Not built" : "Level " + i) + "</option>").join("");
      return '<div class="wl-build"><label>' + b.icon + " " + esc(name) + '</label>' +
        '<select data-b="' + esc(name) + '">' + opts + "</select>" +
        '<div class="bd">' + num(p) + " personal · " + num(a) + " alliance</div></div>";
    }).join("");
    $("builds").querySelectorAll("select").forEach((s) =>
      s.addEventListener("change", () => { buildLevel[s.dataset.b] = +s.value; save(); renderBuilds(); recalc(); }));
  }

  // ---- decoration table ----
  function renderDecos() {
    const q = ($("search").value || "").toLowerCase();
    const rows = DECOS.map((d, i) => ({ d, i }))
      .filter(({ d }) => !q || d.name.toLowerCase().includes(q));
    $("decotbl").innerHTML =
      '<thead><tr><th class="l">Decoration</th><th>Size</th><th>CY capacity</th><th>Wall %</th><th>CY str %</th><th>Count</th></tr></thead><tbody>' +
      rows.map(({ d, i }) => {
        const n = decoQty[i] || 0;
        return '<tr class="' + (n ? "on" : "") + '"><td class="nm">' + esc(d.name) + "</td>" +
          "<td>" + esc(d.size || "—") + "</td>" +
          "<td>" + (d.cy ? "+" + num(d.cy) : "—") + "</td>" +
          "<td>" + (d.wall ? "+" + d.wall + "%" : "—") + "</td>" +
          "<td>" + (d.cystr ? "+" + d.cystr + "%" : "—") + "</td>" +
          '<td><span class="wl-qty"><button data-d="' + i + '" data-s="-1">−</button>' +
          '<input data-d="' + i + '" type="number" min="0" value="' + n + '">' +
          '<button data-d="' + i + '" data-s="1">+</button></span></td></tr>';
      }).join("") + "</tbody>";
    $("decotbl").querySelectorAll("button[data-d]").forEach((b) =>
      b.addEventListener("click", () => { const i = +b.dataset.d; decoQty[i] = Math.max(0, (decoQty[i] || 0) + (+b.dataset.s)); save(); renderDecos(); recalc(); }));
    $("decotbl").querySelectorAll("input[data-d]").forEach((inp) =>
      inp.addEventListener("input", () => { const i = +inp.dataset.d; decoQty[i] = Math.max(0, Math.floor(+inp.value || 0)); save(); recalc(); renderRowState(i, decoQty[i]); }));
  }
  function renderRowState(i, n) {
    const tr = $("decotbl").querySelector('input[data-d="' + i + '"]').closest("tr");
    tr.classList.toggle("on", n > 0);
  }

  // ---- totals ----
  function recalc() {
    let bP = 0, bA = 0;
    Object.entries(BUILDINGS).forEach(([name, b]) => { const [p, a] = b.levels[buildLevel[name]]; bP += p; bA += a; });
    let dCY = 0, dWall = 0, dStr = 0;
    DECOS.forEach((d, i) => { const n = decoQty[i] || 0; if (!n) return; dCY += (d.cy || 0) * n; dWall += (d.wall || 0) * n; dStr += (d.cystr || 0) * n; });

    const cyUsed = Math.min(dCY, CAPS.personalCY);
    const wallUsed = Math.min(dWall, CAPS.wallPct);
    const strUsed = Math.min(dStr, CAPS.cyStrPct);

    const cards = [
      { label: "Personal CY capacity", val: num(bP + cyUsed), sub: num(bP) + " buildings + " + num(cyUsed) + " decos", raw: dCY, cap: CAPS.personalCY, capLabel: "deco cap " + num(CAPS.personalCY), fmt: num },
      { label: "Alliance support cap", val: num(bA), sub: "from buildings", noCap: true },
      { label: "Wall capacity", val: "+" + wallUsed + "%", sub: "decos toward cap", raw: dWall, cap: CAPS.wallPct, capLabel: "cap +" + CAPS.wallPct + "%", fmt: (v) => "+" + v + "%" },
      { label: "CY defence strength", val: "+" + strUsed + "%", sub: "decos toward cap", raw: dStr, cap: CAPS.cyStrPct, capLabel: "cap +" + CAPS.cyStrPct + "%", fmt: (v) => "+" + v + "%" },
    ];
    $("summary").innerHTML = cards.map((c) => {
      if (c.noCap) return '<div class="wl-stat"><div class="l">' + c.label + '</div><div class="v">' + c.val + '</div><div class="sub">' + c.sub + "</div></div>";
      const pct = Math.min(100, Math.round((c.raw / c.cap) * 100));
      const over = c.raw > c.cap;
      const tail = over
        ? '<span class="wl-over">' + c.fmt(c.raw - c.cap) + " over — wasted</span>"
        : '<span class="wl-room">' + c.fmt(c.cap - c.raw) + " room left</span>";
      return '<div class="wl-stat' + (c.raw >= c.cap ? " capped" : "") + '"><div class="l">' + c.label + '</div>' +
        '<div class="v">' + c.val + '</div>' +
        '<div class="sub">' + c.sub + " · " + c.capLabel + '</div>' +
        '<div class="wl-bar' + (over ? " over" : "") + '"><i style="width:' + pct + '%"></i></div>' +
        '<div class="sub">' + tail + "</div></div>";
    }).join("");
  }

  // ---- persistence ----
  function save() {
    try { localStorage.setItem("wl_state", JSON.stringify({ buildLevel, decoQty })); } catch (e) {}
  }
  function loadState() {
    try {
      const s = JSON.parse(localStorage.getItem("wl_state") || "null");
      if (s) { Object.assign(buildLevel, s.buildLevel || {}); Object.assign(decoQty, s.decoQty || {}); }
    } catch (e) {}
  }

  $("search").addEventListener("input", renderDecos);
  $("reset").addEventListener("click", () => {
    Object.keys(decoQty).forEach((k) => delete decoQty[k]);
    Object.keys(BUILDINGS).forEach((n) => { buildLevel[n] = BUILDINGS[n].levels.length - 1; });
    save(); renderBuilds(); renderDecos(); recalc();
  });

  fetch("./data/defence-decos.json")
    .then((r) => r.json())
    .then((d) => {
      DECOS = d.decos || []; if (d.caps) CAPS = d.caps;
      Object.keys(BUILDINGS).forEach((n) => { buildLevel[n] = BUILDINGS[n].levels.length - 1; });
      loadState();
      renderBuilds(); renderDecos(); recalc();
    })
    .catch((e) => { $("summary").innerHTML = '<p class="muted">Could not load decoration data.</p>'; console.error(e); });
})();
