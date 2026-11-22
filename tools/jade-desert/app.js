/* BTH: Jade Edition. One page per tab, reached by #hash so each hub card can
   link straight to its own part. All numbers come from data/jade-desert.json. */
(function () {
  const view = document.getElementById("jd-view");
  const tabsEl = document.getElementById("jd-tabs");
  const titleEl = document.getElementById("jd-title");
  const subEl = document.getElementById("jd-sub");

  const TABS = [
    { id: "citadel", icon: "🏯", name: "Citadel Planner", sub: "What each level costs, how far it reaches, and what you still need." },
    { id: "trades", icon: "🐪", name: "Oasis Trades", sub: "How many troops a trade really gets you, using the same limits as the game." },
    { id: "fortresses", icon: "🏰", name: "Palace Fortresses", sub: "Every fortress tier, its defence and the extra loot it can drop." },
    { id: "crafting", icon: "⚒️", name: "Crafting", sub: "Every Toolsmith and Refinery recipe, with the cost of the 1-hour version." },
    { id: "bonuses", icon: "🛡️", name: "Alliance Bonuses", sub: "All twelve bonuses bought from alliance funds, level by level." },
    { id: "rewards", icon: "🏆", name: "Rewards", sub: "Rank rewards for the alliance and solo rankings." },
    { id: "chest", icon: "🎁", name: "Jade Guardian's Chest", sub: "Drop chances for both phases, and a chest you can spin." },
    { id: "relic", icon: "🗿", name: "Relic Items", sub: "The Jade Stone upgrades that appeared in the game files, then left again." },
  ];

  const fmt = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("en-US"));
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (n) => (n >= 10 ? n.toFixed(1) : n.toFixed(2)) + "%";
  const hrs = (h) => (h === null || h === undefined ? "None listed" : h + " h");
  const costText = (c) => Object.keys(c).map((k) => fmt(c[k]) + " " + esc(k)).join(" + ");
  const intOf = (el) => Math.max(0, Math.floor(Number(el.value) || 0));

  let D = null;
  const state = {
    citadel: { from: 1, to: 6, held: "" },
    trades: { offer: 0, goods: "", room: "", troops: 1000, loot: 100, army: 0, cargo: 0 },
    rewards: { run: "normal", board: "alliance" },
    chest: { phase: "phase1", level: 0, pulls: 0, spent: 0, haul: {} },
  };

  function table(heads, rows, rowClass) {
    const th = heads.map((h) => '<th class="' + (h.n ? "n" : "") + '">' + h.t + "</th>").join("");
    const body = rows.map((r, i) =>
      '<tr class="' + (rowClass ? rowClass(i) : "") + '">' +
      r.map((c, j) => '<td class="' + (heads[j].n ? "n" : "") + '">' + c + "</td>").join("") + "</tr>").join("");
    return '<div class="jd-scroll"><table class="jd"><thead><tr>' + th + "</tr></thead><tbody>" + body + "</tbody></table></div>";
  }

  /* ---- Citadel --------------------------------------------------------- */
  function citadel() {
    const s = state.citadel;
    const levelOpts = (lo, hi, val) => D.citadel.filter((c) => c.level >= lo && c.level <= hi)
      .map((c) => '<option value="' + c.level + '"' + (c.level === val ? " selected" : "") + ">Level " + c.level + "</option>").join("");
    let spent = 0;
    const rows = D.citadel.map((c) => {
      spent += c.cost;
      return ["<b>" + c.level + "</b>", c.radius, c.cost ? fmt(c.cost) : "—", fmt(spent), fmt(c.wallUnits), hrs(c.protectionH)];
    });
    view.innerHTML =
      '<div class="jd-controls">' +
      '<div class="jd-field"><label for="c-from">Citadel now</label><select id="c-from">' + levelOpts(1, 9, s.from) + "</select></div>" +
      '<div class="jd-field"><label for="c-to">Target</label><select id="c-to">' + levelOpts(2, 10, s.to) + "</select></div>" +
      '<div class="jd-field"><label for="c-held">Ancient statuettes ready</label><input id="c-held" type="number" min="0" step="1000" placeholder="0" value="' + esc(s.held) + '" /></div>' +
      "</div>" +
      '<div class="jd-summary" id="c-out"></div>' +
      table([{ t: "Level" }, { t: "Radius", n: 1 }, { t: "Upgrade cost", n: 1 }, { t: "Total parked", n: 1 }, { t: "Wall units", n: 1 }, { t: "Protection", n: 1 }], rows,
        (i) => (D.citadel[i].level === s.to ? "hit" : "")) +
      '<div class="jd-note"><b>Reach:</b> you can only attack what sits inside your citadel radius. A target inside your next level\'s ring shows <b>"Requires Citadel level N"</b> and has no attack button. On our map, neighbours came into reach at <b>level 6</b>. Other spacing can mean another number.</div>' +
      '<div class="jd-note"><b>Upgrading doesn\'t cost points.</b> Statuettes spent on the citadel still convert 1:1 when the event ends. You only lose them if the citadel loses a level.</div>' +
      '<div class="jd-note warn"><b>Level ' + D.event.earlyLevel + " is a different rule.</b> Phase 2 can start early once " + D.event.earlyShare + "% of at least " + D.event.earlyMin + " alliances reach level " + D.event.earlyLevel + ". That switch is server-wide and has nothing to do with your own reach. One of the game's Jade setups has no early switch, so it may simply run the full " + D.event.phase2Hours + " hours.</div>";

    const update = () => {
      s.from = Number(document.getElementById("c-from").value);
      s.to = Number(document.getElementById("c-to").value);
      s.held = document.getElementById("c-held").value;
      const out = document.getElementById("c-out");
      if (s.to <= s.from) {
        out.innerHTML = '<div><span class="lbl">Pick a target above your current level</span><span class="big">—</span></div>';
      } else {
        const steps = D.citadel.filter((c) => c.level > s.from && c.level <= s.to);
        const need = steps.reduce((a, c) => a + c.cost, 0);
        const held = Math.max(0, Number(s.held) || 0);
        const short = need - held;
        const a = D.citadel.find((c) => c.level === s.from), b = D.citadel.find((c) => c.level === s.to);
        out.innerHTML =
          '<div><span class="lbl">Ancient statuettes needed</span><span class="big">' + fmt(need) + "</span></div>" +
          '<div><span class="lbl">' + (short > 0 ? "Still to find" : "Left over") + '</span><span class="big ' + (short > 0 ? "bad" : "good") + '">' + fmt(Math.abs(short)) + "</span></div>" +
          '<div><span class="lbl">Radius</span><span class="big">' + a.radius + " → " + b.radius + "</span></div>";
      }
      view.querySelectorAll("tbody tr").forEach((tr, i) => tr.classList.toggle("hit", D.citadel[i].level === s.to));
    };
    ["c-from", "c-to", "c-held"].forEach((id) => document.getElementById(id).addEventListener("input", update));
    update();
  }

  /* ---- Oasis trades ---------------------------------------------------- */
  function trades() {
    const s = state.trades;
    const opts = D.trades.map((t, i) => '<option value="' + i + '"' + (i === s.offer ? " selected" : "") + ">" + esc(t.gives) + " (" + costText(t.cost) + ")</option>").join("");
    const rows = D.trades.map((t) => [esc(t.gives), costText(t.cost), t.units, fmt(t.capacity), fmt(t.capacity / t.units)]);
    const oasisRows = D.oases.map((o) => ["<b>" + o.level + "</b>", fmt(o.stock), o.level, fmt(o.maxArmy), o.cooldownH + " h"]);
    view.innerHTML =
      '<div class="jd-controls">' +
      '<div class="jd-field"><label for="t-offer">Trade</label><select id="t-offer">' + opts + "</select></div>" +
      '<div class="jd-field"><label for="t-troops">Troops you send</label><input id="t-troops" type="number" min="0" value="' + esc(s.troops) + '" /></div>' +
      '<div class="jd-field"><label for="t-loot">Loot per troop</label><select id="t-loot"><option value="100"' + (s.loot === 100 ? " selected" : "") + '>Dune Carrier (100)</option><option value="50"' + (s.loot === 50 ? " selected" : "") + '>Jade troops (50)</option></select></div>' +
      '<div class="jd-field"><label for="t-army">Trade army size bonus %</label><input id="t-army" type="number" min="0" value="' + esc(s.army) + '" /></div>' +
      '<div class="jd-field"><label for="t-cargo">Loot capacity bonus %</label><input id="t-cargo" type="number" min="0" value="' + esc(s.cargo) + '" /></div>' +
      '<div class="jd-field"><label for="t-room">Oasis stock left</label><input id="t-room" type="number" min="0" placeholder="Not set" value="' + esc(s.room) + '" /></div>' +
      '<div class="jd-field"><label id="t-goods-l" for="t-goods">Batches of goods you hold</label><input id="t-goods" type="number" min="0" placeholder="Not set" value="' + esc(s.goods) + '" /></div>' +
      "</div>" +
      '<div class="jd-summary" id="t-out"></div>' +
      '<div class="jd-note">Each batch uses <b>20</b> of the oasis stock. Stock is only taken when your army <b>lands</b>, so armies already on the way aren\'t in the number the game shows you.</div>' +
      '<h2 class="jd-h">Trade prices</h2>' +
      table([{ t: "You get" }, { t: "Per batch" }, { t: "Troops", n: 1 }, { t: "Loot needed", n: 1 }, { t: "Loot per troop", n: 1 }], rows) +
      '<div class="jd-note warn"><b>Craft first.</b> A crafted batch needs 10 loot capacity per troop, and the raw mix needs 40. The same carriers bring home four times as many troops.</div>' +
      '<h2 class="jd-h">Oasis levels</h2>' +
      table([{ t: "Level" }, { t: "Stock", n: 1 }, { t: "Troop level", n: 1 }, { t: "Army cap", n: 1 }, { t: "Cooldown", n: 1 }], oasisRows) +
      '<div class="jd-note">A used-up oasis comes back <b>one level higher</b> after its cooldown, and higher oases give higher-level troops.</div>';

    const update = () => {
      s.offer = Number(document.getElementById("t-offer").value);
      s.troops = document.getElementById("t-troops").value;
      s.loot = Number(document.getElementById("t-loot").value);
      s.army = document.getElementById("t-army").value;
      s.cargo = document.getElementById("t-cargo").value;
      s.room = document.getElementById("t-room").value;
      s.goods = document.getElementById("t-goods").value;
      const offer = D.trades[s.offer];
      const cap = Math.floor(D.oases[0].maxArmy * (1 + (Number(s.army) || 0) / 100));
      const sent = Math.min(Math.max(0, Math.floor(Number(s.troops) || 0)), cap);
      const lootRoom = Math.floor(s.loot * sent) * (1 + Math.floor(Number(s.cargo) || 0) / 100);
      const limits = [{ why: "loot capacity", lots: Math.floor(lootRoom / offer.capacity) }];
      if (s.room !== "") limits.push({ why: "oasis stock", lots: Math.floor(Math.max(0, Number(s.room)) / offer.stock) });
      if (s.goods !== "") limits.push({ why: "goods you hold", lots: Math.max(0, Math.floor(Number(s.goods))) });
      const best = limits.reduce((a, b) => (b.lots < a.lots ? b : a));
      document.getElementById("t-out").innerHTML =
        '<div><span class="lbl">Batches</span><span class="big">' + fmt(best.lots) + "</span></div>" +
        '<div><span class="lbl">Troops back, before unit bonuses</span><span class="big good">' + fmt(best.lots * offer.units) + "</span></div>" +
        '<div><span class="lbl">Goods used</span><span class="big" style="font-size:1.05rem">' + (costText(Object.fromEntries(Object.entries(offer.cost).map(([k, v]) => [k, v * best.lots])))) + "</span></div>" +
        '<div><span class="lbl">Held back by</span><span class="big" style="font-size:1.05rem">' + best.why + "</span></div>" +
        '<div><span class="lbl">Army cap</span><span class="big" style="font-size:1.05rem">' + fmt(cap) + "</span></div>";
    };
    ["t-offer", "t-troops", "t-loot", "t-army", "t-cargo", "t-room", "t-goods"].forEach((id) => document.getElementById(id).addEventListener("input", update));
    update();
  }

  /* ---- Fortresses ------------------------------------------------------ */
  function fortresses() {
    const f = D.fortresses;
    const tierRows = f.tiers.map((x) => ["<b>" + x.tier + "</b>", x.level, fmt(x.def), fmt(x.pool), "+" + fmt(x.wall) + "%", "+" + fmt(x.gate) + "%", x.guards]);
    const extra = f.extraLoot.map((e) => ['<span class="jd-r' + e.r + '">' + esc(e.n) + "</span>", e.a && e.a > 1 ? fmt(e.a) : "", pct(e.p)]);
    view.innerHTML =
      '<h2 class="jd-h">Three fortress types</h2>' +
      table([{ t: "Fortress" }, { t: "Drops" }], f.types.map((x) => [esc(x.name), esc(x.drops) + " + Ancient Jade Statuettes"])) +
      '<h2 class="jd-h">Tiers</h2>' +
      table([{ t: "Tier" }, { t: "Attack level", n: 1 }, { t: "Defence", n: 1 }, { t: "Loot pool", n: 1 }, { t: "Wall", n: 1 }, { t: "Gate", n: 1 }, { t: "Guards", n: 1 }], tierRows) +
      '<div class="jd-note">All three types share these defences. A used-up fortress returns <b>one tier higher</b> after ' + f.cooldownH + " hours, and travel costs <b>" + (f.travel * 100) + "%</b> of normal. The defender is the <b>Jade Sentinel</b>: +15% melee and ranged defender strength, with no defence tools.</div>" +
      '<div class="jd-note warn"><b>Bring a Jade Idol.</b> In the support slot it adds +10%, +15% or +20% Ancient Statuettes from the fortress.</div>' +
      '<h2 class="jd-h">Extra loot per draw</h2>' +
      table([{ t: "Reward" }, { t: "Amount", n: 1 }, { t: "Chance", n: 1 }], extra);
  }

  /* ---- Crafting -------------------------------------------------------- */
  function crafting() {
    const pairs = {};
    D.crafting.forEach((r) => {
      const key = Math.floor(r.id / 100);
      pairs[key] = pairs[key] || {};
      pairs[key][r.type] = r;
    });
    const rows = Object.values(pairs).map((p) => {
      const l = p.Long, sh = p.Short;
      return [esc(l.building), "<b>" + fmt(l.amount) + " " + esc(l.makes) + "</b>", costText(l.cost), l.hours + " h, free", sh.hours + " h, " + fmt(sh.rubies) + " rubies", fmt(l.skip)];
    });
    view.innerHTML =
      table([{ t: "Building" }, { t: "Makes" }, { t: "Materials" }, { t: "Long" }, { t: "Short" }, { t: "Skip Long (rubies)", n: 1 }], rows) +
      '<div class="jd-note warn"><b>Both versions use the same materials and make the same amount.</b> The Short one costs 100 rubies for finishing in 1 hour instead of 5. Pick Long unless you\'re deliberately paying for speed.</div>';
  }

  /* ---- Alliance bonuses ------------------------------------------------ */
  function bonuses() {
    const val = (b, v) => "+" + fmt(v) + b.unit;
    const block = (b) => {
      const first = b.levels[0], last = b.levels[b.levels.length - 1];
      const timed = b.levels.some((l) => l.hours);
      const heads = [{ t: "Level" }, { t: "Bonus", n: 1 }].concat(timed ? [{ t: "Lasts", n: 1 }] : []).concat([{ t: "Rubies", n: 1 }]);
      const rows = b.levels.map((l) => ["<b>" + l.level + "</b>", val(b, l.value)].concat(timed ? [l.hours + " h"] : []).concat([fmt(l.cost)]));
      const right = b.temporary ? fmt(first.cost) + " to " + fmt(Math.max.apply(null, b.levels.map((l) => l.cost))) + " rubies" : fmt(b.total) + " rubies to max";
      return '<details class="jd-more"><summary><span>' + esc(b.name) + '</span><span class="dim">' + val(b, first.value) + " → " + val(b, Math.max.apply(null, b.levels.map((l) => l.value))) + " · " + right + "</span></summary>" + table(heads, rows) + "</details>";
    };
    const perm = D.bonuses.filter((b) => !b.temporary), temp = D.bonuses.filter((b) => b.temporary);
    const total = perm.reduce((a, b) => a + b.total, 0);
    const cheap = perm.filter((b) => b.total < 500000);
    view.innerHTML =
      '<div class="jd-summary"><div><span class="lbl">All ' + perm.length + ' permanent bonuses</span><span class="big">' + fmt(total) + ' rubies</span></div>' +
      '<div><span class="lbl">The ' + cheap.length + " cheap ones</span><span class=\"big\">" + fmt(cheap.reduce((a, b) => a + b.total, 0)) + " rubies</span></div></div>" +
      '<h2 class="jd-h">Permanent for the event</h2>' + perm.map(block).join("") +
      '<h2 class="jd-h">Temporary</h2>' + temp.map(block).join("") +
      '<div class="jd-note">Paid from alliance funds. Each listed value is the <b>total at that level</b>, so levels don\'t stack on each other. Citadel boosts are bought separately, and the longer 9-hour options cost more for duration, not strength.</div>';
  }

  /* ---- Rewards --------------------------------------------------------- */
  function rewards() {
    const s = state.rewards, R = D.rewards;
    const jadeLive = R.assign.normal && R.assign.normal.alliance === R.jadeSets.alliance;
    const runs = [["normal", "Normal run (live)"], ["beta", "Beta run"]];
    if (!jadeLive) runs.splice(1, 0, ["jade", "Jade tables (not live)"]);
    if (!runs.some((r) => r[0] === s.run)) s.run = "normal";
    const ids = s.run === "jade" ? R.jadeSets : R.assign[s.run];
    const set = R.sets[ids[s.board]];
    const note = {
      normal: jadeLive
        ? "Normal Jade runs pay these tables."
        : "<b>This is what the game is set to pay right now.</b> Normal Jade runs still point at the older Beyond the Horizon reward tables.",
      jade: "<b>Not active yet.</b> These Jade reward tables are in the game files, but no event setting uses them. Goodgame may change them before they go live.",
      beta: "<b>Beta runs hold small placeholder amounts.</b> The game's own notes disagree on the currency, so they're shown as plain numbers. Beta rewards don't carry over.",
    }[s.run];
    const matNames = [];
    set.brackets.forEach((b) => b.items.forEach((i) => { if (!matNames.includes(i.n)) matNames.push(i.n); }));
    const hasBuild = set.brackets.some((b) => b.build.length);
    const heads = [{ t: "Rank" }].concat(matNames.map((n) => ({ t: s.run === "beta" ? "Amount" : esc(n), n: 1 })));
    if (hasBuild) heads.push({ t: "Build items (42 days)" });
    const rows = set.brackets.slice().sort((a, b) => a.from - b.from).map((b) => {
      const rank = b.from === b.to ? fmt(b.from) : fmt(b.from) + "–" + fmt(b.to);
      const cells = matNames.map((n) => { const x = b.items.find((i) => i.n === n); return x ? fmt(x.a) : "—"; });
      const row = ["<b>" + rank + "</b>"].concat(cells);
      if (hasBuild) row.push(b.build.map((x) => esc(x.name) + (x.tier ? " T" + x.tier : "") + (x.effect ? ' <span class="dim">' + esc(x.effect) + "</span>" : "")).join("<br>") || "—");
      return row;
    });
    const btn = (group, id, label, on) => '<button class="jd-btn' + (on ? " on" : "") + '" data-' + group + '="' + id + '">' + label + "</button>";
    view.innerHTML =
      '<div class="jd-controls"><div class="jd-toggle">' + runs.map((r) => btn("run", r[0], r[1], r[0] === s.run)).join("") + "</div>" +
      '<div class="jd-toggle">' + btn("board", "alliance", "Alliance ranking", s.board === "alliance") + btn("board", "solo", "Solo ranking", s.board === "solo") + "</div></div>" +
      '<div class="jd-note ' + (s.run === "normal" ? "" : "warn") + '">' + note + "</div>" + table(heads, rows);
    view.querySelectorAll("[data-run]").forEach((b) => (b.onclick = () => { s.run = b.dataset.run; rewards(); }));
    view.querySelectorAll("[data-board]").forEach((b) => (b.onclick = () => { s.board = b.dataset.board; rewards(); }));
  }

  /* ---- Chest ----------------------------------------------------------- */
  function levelForPull(levels, pull) {
    return levels.find((l) => pull >= l.from && (l.to === null || pull <= l.to)) || levels[levels.length - 1];
  }

  function spin(level) {
    let roll = Math.random() * level.entries.reduce((a, e) => a + e.p, 0);
    for (const e of level.entries) {
      roll -= e.p;
      if (roll <= 0) return e;
    }
    return level.entries[level.entries.length - 1];
  }

  function chest() {
    const s = state.chest, levels = D.gacha[s.phase], L = levels[s.level];
    const span = (l) => (l.to === null ? l.from + "+" : l.from === l.to ? String(l.from) : l.from + "–" + l.to);
    const rows = L.entries.map((e) => ['<span class="jd-r' + e.r + '">' + esc(e.n) + "</span>", e.a && e.a > 1 ? "×" + fmt(e.a) : "", pct(e.p)]);
    const nextPull = s.pulls + 1, nextL = levelForPull(levels, nextPull);
    const haul = Object.values(s.haul).sort((a, b) => b.count - a.count);
    view.innerHTML =
      '<div class="jd-controls"><div class="jd-toggle">' +
      '<button class="jd-btn' + (s.phase === "phase1" ? " on" : "") + '" data-phase="phase1">Phase 1 pool</button>' +
      '<button class="jd-btn' + (s.phase === "phase2" ? " on" : "") + '" data-phase="phase2">Phase 2 pool</button></div></div>' +
      '<div class="jd-note">The chest resets every 24 hours and pulls count from level 1 again. Each pull costs <b>' + L.cost + " Jade Gacha Tokens</b>. Phase 1 is mostly Fortress Breaker and Caravaneer gear. From the switch, Phase 2 is mostly Conqueror and Warden. Each pool still holds a little of the other set.</div>" +
      '<div class="jd-ladder">' + levels.map((l, i) => '<button class="' + (l.bonus ? "bonus " : "") + (i === s.level ? "on" : "") + '" data-level="' + i + '">' + l.label + " · " + span(l) + "</button>").join("") + "</div>" +
      '<h2 class="jd-h">' + L.label + " · pull" + (L.from === L.to ? " " : "s ") + span(L) + "</h2>" +
      table([{ t: "Reward" }, { t: "Amount", n: 1 }, { t: "Chance", n: 1 }], rows) +
      '<h2 class="jd-h">Spin it</h2>' +
      '<div class="jd-controls"><div class="jd-toggle">' +
      '<button class="jd-btn" data-spin="1">Pull 1</button><button class="jd-btn" data-spin="10">Pull 10</button><button class="jd-btn" data-spin="50">Pull 50</button><button class="jd-btn" data-spin="0">New day</button></div></div>' +
      '<div class="jd-summary"><div><span class="lbl">Pulls today</span><span class="big">' + fmt(s.pulls) + '</span></div><div><span class="lbl">Tokens spent</span><span class="big">' + fmt(s.spent) + '</span></div><div><span class="lbl">Next pull</span><span class="big" style="font-size:1.05rem">' + nextL.label + "</span></div></div>" +
      (haul.length ? '<div class="jd-haul">' + table([{ t: "You got" }, { t: "Times", n: 1 }, { t: "Total", n: 1 }], haul.map((h) => ['<span class="jd-r' + h.r + '">' + esc(h.n) + "</span>", fmt(h.count), h.a > 1 ? fmt(h.a * h.count) : ""])) + "</div>" : "");
    view.querySelectorAll("[data-phase]").forEach((b) => (b.onclick = () => { s.phase = b.dataset.phase; chest(); }));
    view.querySelectorAll("[data-level]").forEach((b) => (b.onclick = () => { s.level = Number(b.dataset.level); chest(); }));
    view.querySelectorAll("[data-spin]").forEach((b) => (b.onclick = () => {
      const n = Number(b.dataset.spin);
      if (!n) { s.pulls = 0; s.spent = 0; s.haul = {}; s.level = 0; return chest(); }
      for (let i = 0; i < n; i++) {
        s.pulls++;
        const lvl = levelForPull(D.gacha[s.phase], s.pulls);
        s.spent += lvl.cost;
        const e = spin(lvl), key = e.n + "|" + e.a;
        s.haul[key] = s.haul[key] || { n: e.n, a: e.a || 1, r: e.r, count: 0 };
        s.haul[key].count++;
      }
      s.level = levels.indexOf(levelForPull(levels, s.pulls + 1));
      chest();
    }));
  }

  /* ---- Relic ----------------------------------------------------------- */
  function relic() {
    const r = D.relic;
    const show = (o) => Object.keys(o).map((k) => "+" + o[k] + "% " + esc(k)).join("<br>");
    const rows = r.families.map((f) => ["<b>" + esc(f.name) + "</b>", show(f.now), show(f.preview), fmt(f.jadeStones)]);
    view.innerHTML =
      (r.live
        ? '<div class="jd-note warn"><b>Levels 31–60 are back in the game files.</b> The figures below are from the ' + esc(r.version) + " snapshot, so check prices in-game.</div>"
        : '<div class="jd-note bad"><b>Not in the game right now.</b> Update ' + esc(r.version) + " added these upgrades, then the next update removed them again. In the current files (" + esc(D.itemsVersion) + ") these items still stop at level 30 at the old prices. Treat this as a preview of what may return.</div>") +
      table([{ t: "Build item" }, { t: "Level 30 today" }, { t: "Level 60 in the preview" }, { t: "Jade Stones, 31–60", n: 1 }], rows) +
      '<h2 class="jd-h">How the preview priced it</h2>' +
      '<div class="jd-note">Jade Stones rose by <b>10 per level</b>, from 10 at level 31 to 300 at level 60. Odd levels also took 18,750 Timber, 9,375 Nails and 1,875 Cobblestone. Even levels took 14,100 Straw, 4,725 Glue and 75 Fabric. Levels 1–30 dropped to about a quarter of their current material cost.</div>' +
      '<div class="jd-note">Jade Stones come from the solo ranking table, which is <b>not live yet</b> either. See <a href="#rewards">Rewards</a>.</div>';
  }

  const RENDER = { citadel, trades, fortresses, crafting, bonuses, rewards, chest, relic };

  function route() {
    const id = location.hash.replace("#", "");
    const tab = TABS.find((t) => t.id === id) || TABS[0];
    tabsEl.querySelectorAll("a").forEach((a) => a.classList.toggle("on", a.dataset.id === tab.id));
    titleEl.textContent = tab.icon + " " + tab.name;
    subEl.textContent = tab.sub;
    document.title = tab.name + " — BTH: Jade Edition";
    RENDER[tab.id]();
  }

  tabsEl.innerHTML = TABS.map((t) => '<a href="#' + t.id + '" data-id="' + t.id + '">' + t.icon + " " + t.name + "</a>").join("");
  window.addEventListener("hashchange", route);

  fetch("data/jade-desert.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => {
      D = data;
      document.getElementById("jd-foot").textContent =
        "From the game's own files, version " + D.itemsVersion + ". Game data belongs to Goodgame Studios.";
      route();
    })
    .catch(() => { view.innerHTML = '<div class="jd-note bad">Couldn\'t load the Jade Desert data. Refresh to try again.</div>'; });
})();
