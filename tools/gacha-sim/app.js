/* Gacha Spin Simulator — Maxy's Empire Toolkit
   Real drop data per game version. Pick event + version + level, read the odds,
   then run weighted-random spins. */

const RARITY = { 1: "Common", 2: "Rare", 3: "Epic", 4: "Legendary" };
const $ = (id) => document.getElementById(id);

let MANIFEST = null;       // { latest, versions:[...] }
const versionCache = {};   // ver -> events array
let events = null;         // current version's events
let event = null;          // selected event
let pool = null;           // selected level's pool { total, entries }
let stats = null;

// ---- boot ----------------------------------------------------------------
fetch("./data/versions.json")
  .then((r) => r.json())
  .then((m) => { MANIFEST = m; initVersions(); })
  .catch((e) => { fail(); console.error(e); });

function fail() {
  $("poolmeta").innerHTML = '<span class="muted">Could not load game data.</span>';
}

function initVersions() {
  const sel = $("version");
  sel.innerHTML = MANIFEST.versions
    .map((v) => '<option value="' + v + '">' + v + (v === MANIFEST.latest ? "  (latest)" : "") + "</option>")
    .join("");
  sel.value = MANIFEST.latest;
  sel.addEventListener("change", () => loadVersion(sel.value));

  $("event").addEventListener("change", () => selectEvent($("event").value));
  $("level").addEventListener("change", () => selectLevel(parseInt($("level").value, 10)));

  loadVersion(MANIFEST.latest);
}

function loadVersion(ver) {
  if (versionCache[ver]) { applyVersion(versionCache[ver]); return; }
  fetch("./data/gacha-" + ver + ".json")
    .then((r) => r.json())
    .then((d) => { cleanData(d.events); versionCache[ver] = d.events; applyVersion(d.events); })
    .catch((e) => { fail(); console.error(e); });
}

function applyVersion(evts) {
  events = evts;
  const prev = $("event").value;
  $("event").innerHTML = events
    .map((e) => '<option value="' + e.eventID + '">' + esc(e.name) + "</option>")
    .join("");
  // keep the same event selected across version switches when possible
  if (events.some((e) => e.eventID === prev)) $("event").value = prev;
  selectEvent($("event").value);
}

function selectEvent(eventID) {
  event = events.find((e) => e.eventID === eventID) || events[0];
  const prevLvl = parseInt($("level").value, 10);
  $("level").innerHTML = event.levels
    .map((l) => '<option value="' + l.level + '">Level ' + l.level + "</option>")
    .join("");
  if (event.levels.some((l) => l.level === prevLvl)) $("level").value = prevLvl;
  selectLevel(parseInt($("level").value, 10));
}

function selectLevel(level) {
  const lvl = event.levels.find((l) => l.level === level) || event.levels[0];
  pool = lvl;
  resetStats();
  renderMeta(lvl);
  renderOdds();
  renderTargets();
}

// Make repeated names within a pool distinct, tidy stray "Misc" labels.
function cleanData(evts) {
  const ROMAN = ["", "", " II", " III", " IV", " V", " VI", " VII", " VIII", " IX", " X"];
  evts.forEach((ev) =>
    ev.levels.forEach((l) => {
      const seen = new Map();
      l.entries.forEach((e) => {
        if (window.ggeFixName) e.name = window.ggeFixName(e.name);
        if (e.type === "Misc" && /^(Common|Rare|Epic|Legendary|Reward)$/.test(e.name)) e.name = "Mystery reward";
        const base = e.name;
        const n = (seen.get(base) || 0) + 1;
        seen.set(base, n);
        if (n > 1) e.name = base + (ROMAN[n] || " #" + n);
      });
    })
  );
}

// ---- odds ----------------------------------------------------------------
function pct(shares) { return (shares / pool.total) * 100; }
function fmtPct(p) { return p >= 10 ? p.toFixed(1) : p >= 1 ? p.toFixed(2) : p.toFixed(3); }

function renderMeta(lvl) {
  const cost = lvl.cost ? lvl.cost.amount + " " + prettyCost(lvl.cost.what) : "—";
  $("poolmeta").innerHTML =
    "<span><b>" + pool.entries.length + "</b> possible rewards</span>" +
    "<span>Cost per spin: <b>" + cost + "</b></span>" +
    "<span>Game version: <b>" + $("version").value + "</b></span>";
}
function prettyCost(w) {
  if (!w) return "";
  return String(w).replace(/([A-Z])/g, " $1").trim();
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
      const nameHtml = e.type === "Equipment"
        ? '<a class="eq-link" href="../overview-equipment/?q=' + encodeURIComponent(e.name) + '">' + esc(e.name) + "</a>"
        : esc(e.name);
      return (
        '<tr><td class="r' + e.rarity + '">' + nameHtml + amt +
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
  const byName = new Map();
  pool.entries.forEach((e) => byName.set(e.name, (byName.get(e.name) || 0) + e.shares));
  const items = [...byName.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  sel.innerHTML = '<option value="">— pick to see pulls-to-get —</option>' +
    items.map(([name, sh]) => '<option value="' + esc(name) + '">' + esc(name) +
      " (" + fmtPct(pct(sh)) + "%)</option>").join("");
  sel.onchange = () => {
    const name = sel.value;
    if (!name) { $("targetHint").textContent = ""; return; }
    const p = byName.get(name) / pool.total;
    const avg = Math.round(1 / p);
    const n90 = p >= 1 ? 1 : Math.ceil(Math.log(0.1) / Math.log(1 - p));
    $("targetHint").textContent = "Avg " + avg + " spins · 90% chance within " + n90 + " spins";
  };
  $("targetHint").textContent = "";
}

// ---- simulation ----------------------------------------------------------
function resetStats() {
  stats = { pulls: 0, rarity: [0, 0, 0, 0, 0], items: new Map(), best: null };
  renderSim(null);
}
function drawOne() {
  let roll = Math.random() * pool.total;
  for (const e of pool.entries) { roll -= e.shares; if (roll <= 0) return e; }
  return pool.entries[pool.entries.length - 1];
}
function spin(n) {
  const got = [];
  for (let i = 0; i < n; i++) {
    stats.pulls++;
    const e = drawOne();
    got.push(e);
    stats.rarity[e.rarity]++;
    const row = stats.items.get(e.name) || { name: e.name, rarity: e.rarity, qty: 0 };
    row.qty++;
    stats.items.set(e.name, row);
    if (!stats.best || e.rarity > stats.best.rarity) stats.best = e;
  }
  renderSim(got);
}
function renderSim(lastGot) {
  $("statPulls").textContent = stats.pulls.toLocaleString();
  const lvl = event ? event.levels.find((l) => l.level === pool.level) : null;
  const each = lvl && lvl.cost ? lvl.cost.amount : 0;
  $("statCost").textContent = each ? (stats.pulls * each).toLocaleString() : "—";
  $("statBest").innerHTML = stats.best
    ? '<span class="r' + stats.best.rarity + '">' + esc(stats.best.name) + "</span>" : "—";

  const total = stats.rarity.reduce((a, b) => a + b, 0);
  $("rarityBar").innerHTML = [1, 2, 3, 4]
    .map((r) => '<span class="s' + r + '" style="width:' + (total ? (stats.rarity[r] / total) * 100 : 0) + '%"></span>')
    .join("");

  const last = new Set((lastGot || []).map((e) => e.name));
  const rows = [...stats.items.values()]
    .sort((a, b) => b.rarity - a.rarity || b.qty - a.qty)
    .map((it) =>
      '<div class="row' + (last.has(it.name) ? " flash" : "") + '">' +
      '<span class="r' + it.rarity + '"><span class="dot r' + it.rarity + '"></span>' +
      esc(it.name) + '</span><span class="qty">×' + it.qty + "</span></div>")
    .join("");
  $("haul").innerHTML = rows || '<p class="muted">Spin to start collecting.</p>';
}

// ---- wiring --------------------------------------------------------------
document.querySelectorAll(".btn[data-pulls]").forEach((b) =>
  b.addEventListener("click", () => spin(parseInt(b.dataset.pulls, 10))));
$("resetBtn").addEventListener("click", resetStats);

function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
