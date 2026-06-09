/* Gacha Spin Simulator — Empire Toolbox
   Loads real drop data (data/gacha-data.json) and runs weighted-random spins. */

const RARITY = { 1: "Common", 2: "Rare", 3: "Epic", 4: "Legendary" };
const $ = (id) => document.getElementById(id);

let DATA = null;
let pool = null;       // { total, entries:[{name,type,amount,rarity,shares}] }
let source = null;     // selected event/lootbox meta { name, tombolaID, cost, spins, ... }
let stats = null;      // running simulation state

// ---- load ----------------------------------------------------------------
fetch("./data/gacha-data.json")
  .then((r) => r.json())
  .then((d) => { DATA = d; cleanData(); initSources(); })
  .catch((e) => {
    $("poolmeta").innerHTML = '<span class="muted">Could not load game data.</span>';
    console.error(e);
  });

// Tidy names: relabel rarity-word "Misc" entries, and make repeated names in a
// pool distinct (they're genuinely different items sharing a dev label).
function cleanData() {
  const ROMAN = ["", "", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"];
  const rarityWord = new Set(["Common", "Rare", "Epic", "Legendary", "Reward"]);
  Object.values(DATA.pools).forEach((p) => {
    const seen = new Map();
    p.entries.forEach((e) => {
      if (e.type === "Misc" && rarityWord.has(e.name)) e.name = "Mystery reward";
      const base = e.name;
      const n = (seen.get(base) || 0) + 1;
      seen.set(base, n);
      if (n > 1) e.name = base + (ROMAN[n] || " #" + n);
    });
  });
}

function initSources() {
  const sel = $("source");
  const has = (id) => DATA.pools[id] && DATA.pools[id].entries.length;

  const gEvents = DATA.gachaEvents.filter((e) => has(e.tombolaID));
  const boxes = DATA.lootBoxes.filter((b) => has(b.tombolaID));

  const optg = (label, items, kind) => {
    const g = document.createElement("optgroup");
    g.label = label;
    items.forEach((it) => {
      const o = document.createElement("option");
      o.value = kind + ":" + it.id;
      o.textContent = it.name + (it.cost ? "  (cost " + it.cost + ")" : "");
      g.appendChild(o);
    });
    return g;
  };

  sel.innerHTML = "";
  if (gEvents.length) sel.appendChild(optg("Gacha events", gEvents, "g"));
  if (boxes.length) sel.appendChild(optg("Loot boxes", boxes, "b"));

  sel.addEventListener("change", () => selectSource(sel.value));
  selectSource(sel.value);
}

function selectSource(value) {
  const [kind, id] = value.split(":");
  source =
    kind === "g"
      ? DATA.gachaEvents.find((e) => e.id === id)
      : DATA.lootBoxes.find((b) => b.id === id);
  pool = DATA.pools[source.tombolaID];
  resetStats();
  renderMeta();
  renderOdds();
  renderTargets();
}

// ---- odds ----------------------------------------------------------------
function pct(shares) { return (shares / pool.total) * 100; }
function fmtPct(p) { return p >= 10 ? p.toFixed(1) : p >= 1 ? p.toFixed(2) : p.toFixed(3); }

function renderMeta() {
  const spins = source.spins || 1;
  const cost = source.cost != null ? source.cost : "—";
  $("poolmeta").innerHTML =
    "<span><b>" + pool.entries.length + "</b> possible rewards</span>" +
    "<span>Cost per spin: <b>" + cost + "</b></span>" +
    "<span>Items per spin: <b>" + spins + "</b></span>" +
    (source.maxPulls ? "<span>Pull limit: <b>" + source.maxPulls + "</b></span>" : "");
}

function renderOdds() {
  const counts = [0, 0, 0, 0, 0];
  pool.entries.forEach((e) => (counts[e.rarity] += pct(e.shares)));
  $("legend").innerHTML = [1, 2, 3, 4]
    .map((r) => '<span class="r' + r + '"><span class="dot r' + r + '"></span>' +
      RARITY[r] + " " + fmtPct(counts[r]) + "%</span>")
    .join("");

  const rows = pool.entries
    .map((e) => {
      const amt = e.amount != null && e.amount !== 1 ? '<span class="amt"> ×' + e.amount + "</span>" : "";
      return (
        '<tr><td class="r' + e.rarity + '">' + esc(e.name) + amt +
        '</td><td class="amt">' + (e.type || "") +
        '</td><td class="pct">' + fmtPct(pct(e.shares)) + "%</td></tr>"
      );
    })
    .join("");
  $("oddsTable").innerHTML =
    "<thead><tr><th>Reward</th><th>Type</th><th>Chance</th></tr></thead><tbody>" + rows + "</tbody>";
}

// ---- targets (pulls-to-get) ---------------------------------------------
function renderTargets() {
  const sel = $("target");
  // unique reward names, keep best (highest) chance per name
  const byName = new Map();
  pool.entries.forEach((e) => {
    const cur = byName.get(e.name) || 0;
    byName.set(e.name, cur + e.shares);
  });
  const items = [...byName.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  sel.innerHTML = '<option value="">— pick to see pulls-to-get —</option>' +
    items.map(([name, sh]) => '<option value="' + esc(name) + '">' + esc(name) +
      " (" + fmtPct(pct(sh)) + "%)</option>").join("");
  sel.onchange = () => {
    const name = sel.value;
    if (!name) { $("targetHint").textContent = ""; return; }
    const sh = byName.get(name);
    const p = sh / pool.total;
    const avg = 1 / p;
    const n90 = Math.ceil(Math.log(0.1) / Math.log(1 - p));
    $("targetHint").textContent =
      "Avg " + Math.round(avg) + " spins · 90% chance within " + n90 + " spins";
  };
  $("targetHint").textContent = "";
}

// ---- simulation ----------------------------------------------------------
function resetStats() {
  stats = { pulls: 0, cost: 0, rarity: [0, 0, 0, 0, 0], items: new Map(), best: null };
  renderSim(null);
}

function drawOne() {
  let roll = Math.random() * pool.total;
  for (const e of pool.entries) {
    roll -= e.shares;
    if (roll <= 0) return e;
  }
  return pool.entries[pool.entries.length - 1];
}

function spin(n) {
  const spins = source.spins || 1;
  const got = [];
  for (let i = 0; i < n; i++) {
    stats.pulls++;
    if (source.cost != null) stats.cost += source.cost;
    for (let s = 0; s < spins; s++) {
      const e = drawOne();
      got.push(e);
      stats.rarity[e.rarity]++;
      const key = e.name;
      const row = stats.items.get(key) || { name: e.name, rarity: e.rarity, type: e.type, qty: 0 };
      row.qty++;
      stats.items.set(key, row);
      if (!stats.best || e.rarity > stats.best.rarity) stats.best = e;
    }
  }
  renderSim(got);
}

function renderSim(lastGot) {
  $("statPulls").textContent = stats.pulls.toLocaleString();
  $("statCost").textContent = stats.cost.toLocaleString();
  $("statBest").innerHTML = stats.best
    ? '<span class="r' + stats.best.rarity + '">' + esc(stats.best.name) + "</span>"
    : "—";

  const totalItems = stats.rarity.reduce((a, b) => a + b, 0);
  $("rarityBar").innerHTML = [1, 2, 3, 4]
    .map((r) => {
      const w = totalItems ? (stats.rarity[r] / totalItems) * 100 : 0;
      return '<span class="s' + r + '" style="width:' + w + '%"></span>';
    })
    .join("");

  const lastNames = new Set((lastGot || []).map((e) => e.name));
  const rows = [...stats.items.values()]
    .sort((a, b) => b.rarity - a.rarity || b.qty - a.qty)
    .map((it) =>
      '<div class="row' + (lastNames.has(it.name) ? " flash" : "") + '">' +
      '<span class="r' + it.rarity + '"><span class="dot r' + it.rarity + '"></span>' +
      esc(it.name) + '</span><span class="qty">×' + it.qty + "</span></div>"
    )
    .join("");
  $("haul").innerHTML = rows || '<p class="muted">Spin to start collecting.</p>';
}

// ---- wiring --------------------------------------------------------------
document.querySelectorAll(".btn[data-pulls]").forEach((b) =>
  b.addEventListener("click", () => spin(parseInt(b.dataset.pulls, 10)))
);
$("resetBtn").addEventListener("click", resetStats);

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
