/* Rift Commander Maker */
(function () {
  "use strict";

  const DATA_URL = "./data/rift.json";
  const STORAGE_KEY = "rift_owned_v2";
  const EQUIP_SLOTS = ["Armor", "Weapon", "Helmet", "Artifact", "Hero"];
  const SLOT_EMOJI = { Armor: "🛡️", Weapon: "⚔️", Helmet: "⛑️", Artifact: "🏺", Hero: "👑" };
  const GEM_LABELS = ["Socket I", "Socket II", "Socket III", "Socket IV"];

  /* Human-readable labels for unresolved effect codes */
  const EFFECT_LABELS = {
    featureAutoSpy: (v) => `Auto-spy on nearby enemies (${v} charges)`,
    featureLoyaltyGift: (v) => `Loyalty gift charges +${v}`,
    attackUnitAmountFlankShapeshifter: (v) => `+${v}% unit limit on the flanks (Shapeshifter attack)`,
    attackBoostYardShapeshifter: (v) => `+${v}% courtyard attack strength (Shapeshifter)`,
    BGCollectorBoost: (v) => `+${v}% collector production`,
    baseRecruitmentTimeBoost: (v) => `-${v}% recruitment time`,
    buildingCostsBoost: (v) => `-${v}% building costs`,
    charmBoost: (v) => `+${v} charm`,
    foodCapacityBonusGreen: (v) => `+${v}% food capacity`,
    gloryDecayBoost: () => "Reduced glory decay on all ranks",
    recruitmentSlotsBonus: (v) => `+${v.split("+")[1] || v} recruitment slots`,
    researchCostsBoost: (v) => `-${v}% research costs`,
  };

  function prettifyLabel(raw) {
    const label = raw.trim();
    if (label.startsWith("+") || label.startsWith("-")) return label;
    const space = label.indexOf(" ");
    if (space === -1) return label;
    const code = label.slice(0, space);
    const val = label.slice(space + 1);
    const fn = EFFECT_LABELS[code];
    return fn ? fn(val) : label;
  }

  /* ---- Effect weighting ----------------------------------------------------
     The optimizer scores a loadout by the weighted sum of its combat effects
     (plus the effects of any set bonuses it lights up), NOT just piece count.
     Priority, per category:
       1. Range / Melee / Courtyard attack    (primary damage)   — highest
       2. Flank / Front unit limit            (more units in)    — high
       3. Flank / Front combat strength       (per-unit damage)  — medium
       4. Rift wall-break utility             (breach windows)   — medium
       5. Speed / moat / misc                                    — low
       6. Event tokens / economy                                — negligible
  ---------------------------------------------------------------------------- */
  const STAT_CATEGORIES = [
    /* Primary damage — what actually clears walls and courtyard. */
    { id: "rangeAtk",  label: "Range attack",      weight: 10, test: (n) => n.includes("offensiverangedbonus") },
    { id: "meleeAtk",  label: "Melee attack",      weight: 10, test: (n) => n.includes("offensivemeleebonus") },
    { id: "courtyard", label: "Courtyard attack",  weight: 10, test: (n) => n.includes("offensiveyardstr") },
    /* Extra waves multiply the whole attack — but per-wave value is small next
       to a +%-stat, so scale modestly. */
    { id: "waves",     label: "Extra waves",       weight: 120, test: (n) => n.includes("additionalwaves") },
    { id: "limit",     label: "Flank/front limit", weight: 6,  test: (n) => n.includes("attackunitamount") },
    { id: "frontFlankStr", label: "Flank/front str", weight: 3, test: (n) => /offensivefrontstr|offensiveflankstr/.test(n) },
    { id: "breach",    label: "Wall-break delay",  weight: 4,  test: (n) => n.includes("wallregenerationdelay") },
    { id: "protect",   label: "Wall/gate protection", weight: 1, test: (n) => /arewallprotection|aregateprotection/.test(n) },
    { id: "minor",     label: "Speed / misc",      weight: 0.5, test: (n) => /speedbonus|returntravelboost/.test(n) },
    /* Boss-specific gimmicks (reserve kills, zombie-infection protection) only
       matter on one boss — weight LAST so they never drive the build. */
    { id: "bossSpec",  label: "Boss-specific",     weight: 0.0005, test: (n) => n.startsWith("reserveunitkill") || n.includes("infectionrate") },
  ];
  const ECON_WEIGHT = 0.02; // anything uncategorised — below boss-specific only barely

  /* Optimisation goals — multipliers applied ON TOP of the base weights, so
     you can tell the optimizer what this commander is FOR. */
  const PRESETS = {
    balanced:  { label: "⚖️ Balanced",        mult: {} },
    ranged:    { label: "🏹 Ranged focus",    mult: { rangeAtk: 3, meleeAtk: 0.3 } },
    melee:     { label: "⚔️ Melee focus",     mult: { meleeAtk: 3, rangeAtk: 0.3 } },
    courtyard: { label: "🏯 Courtyard clear", mult: { courtyard: 3, waves: 1.5 } },
    wallbreak: { label: "🧱 Wall breaker",    mult: { breach: 6, limit: 1.5, frontFlankStr: 1.5, courtyard: 0.3 } },
  };
  let curPreset = "balanced";

  const CAT_EMOJI = {
    rangeAtk: "🏹", meleeAtk: "⚔️", courtyard: "🏯", waves: "🌊", bossSpec: "💀",
    limit: "👥", frontFlankStr: "💪", breach: "⏱️", protect: "🛡️", minor: "🐎",
  };

  function effectCategory(name) {
    const n = (name || "").toLowerCase();
    for (const c of STAT_CATEGORIES) if (c.test(n)) return c;
    return null;
  }
  function effectWeight(name) {
    const c = effectCategory(name);
    if (!c) return ECON_WEIGHT;
    const m = (PRESETS[curPreset].mult[c.id] != null) ? PRESETS[curPreset].mult[c.id] : 1;
    return c.weight * m;
  }

  let allSets = [];
  let qty = {};            // id -> owned count

  /* ---- State (quantities; migrates the old own/not-own set) ---- */
  const QTY_KEY = "rift_qty_v3";
  function loadOwned() {
    qty = {};
    try {
      const s = localStorage.getItem(QTY_KEY);
      if (s) { qty = JSON.parse(s) || {}; return; }
      const old = localStorage.getItem(STORAGE_KEY);
      if (old) {
        for (const id of JSON.parse(old)) qty[String(id)] = 1;
        saveOwned();
      }
    } catch (e) { qty = {}; }
  }
  function saveOwned() {
    localStorage.setItem(QTY_KEY, JSON.stringify(qty));
  }
  function getQty(id) { return qty[String(id)] || 0; }
  function setQty(id, n) {
    id = String(id);
    n = Math.max(0, Math.min(99, n | 0));
    if (n === 0) delete qty[id]; else qty[id] = n;
    saveOwned();
  }

  function countOwnedInSet(set) {
    let n = 0;
    for (const it of set.items) if (getQty(it.id) > 0) n++;
    for (const g of set.gems) if (getQty(g.id) > 0) n++;
    return n;
  }
  function totalOwnedPieces() {
    return Object.values(qty).reduce((a, b) => a + b, 0);
  }

  /* ---- Optimizer ---- */
  /* `pool` maps id -> remaining count, so multi-commander builds consume gear. */
  function buildCandidates(pool) {
    const bySlot = {};
    for (const slot of EQUIP_SLOTS) bySlot[slot] = [];
    const byGem = [[], [], [], []];

    for (const set of allSets) {
      for (const item of set.items) {
        if ((pool[String(item.id)] || 0) > 0) bySlot[item.slot].push({ setID: set.setID, item, set });
      }
      for (const gem of set.gems) {
        if ((pool[String(gem.id)] || 0) > 0) byGem[gem.gemType].push({ setID: set.setID, gem, set });
      }
    }
    return { bySlot, byGem };
  }

  /* Sum weighted effect value into a totals object (by category) and return
     the weighted contribution to the overall score. */
  function addEffects(effects, totals) {
    let s = 0;
    for (const e of effects || []) {
      const w = effectWeight(e.name);
      const v = (e.value || 0) * w;
      s += v;
      const cat = effectCategory(e.name);
      const key = cat ? cat.id : "econ";
      totals[key] = (totals[key] || 0) + (e.value || 0);
    }
    return s;
  }

  /* Weighted score of a loadout: every equipped effect plus the effects of any
     set bonuses it unlocks, each scaled by its category weight. Returns both the
     scalar score and per-category raw totals for display. */
  function evaluateAssignment(assignment) {
    const counts = {};
    const totals = {};
    let score = 0;

    for (const v of Object.values(assignment)) {
      if (!v) continue;
      counts[v.setID] = (counts[v.setID] || 0) + 1;
      const fx = v.item ? v.item.effects : v.gem ? v.gem.effects : [];
      score += addEffects(fx, totals);
    }
    for (const [sid, cnt] of Object.entries(counts)) {
      const set = allSets.find((s) => s.setID === +sid);
      if (!set) continue;
      for (const bonus of set.bonuses) {
        if (bonus.pieces <= cnt) score += addEffects(bonus.effects, totals);
      }
    }
    return { score, totals, counts };
  }

  function scoreAssignment(assignment) {
    return evaluateAssignment(assignment).score;
  }

  function runOptimizer(pool) {
    const { bySlot, byGem } = buildCandidates(pool);
    const ALL_SLOT_KEYS = [...EQUIP_SLOTS, "gem0", "gem1", "gem2", "gem3"];

    const candidates = {
      Armor: bySlot.Armor,
      Weapon: bySlot.Weapon,
      Helmet: bySlot.Helmet,
      Artifact: bySlot.Artifact,
      Hero: bySlot.Hero,
      gem0: byGem[0],
      gem1: byGem[1],
      gem2: byGem[2],
      gem3: byGem[3],
    };

    /* Count combinations (each slot: N choices + 1 "empty") */
    let combos = 1;
    for (const key of ALL_SLOT_KEYS) combos *= (candidates[key].length + 1);

    let best = null;
    let bestScore = -1;

    if (combos <= 500000) {
      /* Full exhaustive search */
      function search(idx, assign) {
        if (idx === ALL_SLOT_KEYS.length) {
          const s = scoreAssignment(assign);
          if (s > bestScore) { bestScore = s; best = { ...assign }; }
          return;
        }
        const key = ALL_SLOT_KEYS[idx];
        const cands = candidates[key];
        for (const c of cands) { assign[key] = c; search(idx + 1, assign); }
        assign[key] = null;
        search(idx + 1, assign);
      }
      search(0, {});
    } else {
      /* Greedy: try every possible "primary set" with best fill for each slot */
      const tryAssign = (assign) => {
        const s = scoreAssignment(assign);
        if (s > bestScore) { bestScore = s; best = { ...assign }; }
      };

      const setIDs = allSets.map((s) => s.setID);

      /* Pure single-set solutions */
      for (const sid of setIDs) {
        const assign = {};
        for (const key of ALL_SLOT_KEYS) {
          const c = candidates[key].find((x) => x.setID === sid);
          assign[key] = c || null;
        }
        tryAssign(assign);
      }

      /* Two-set solutions: for each pair, try both orderings of slot priority */
      for (let i = 0; i < setIDs.length; i++) {
        for (let j = i + 1; j < setIDs.length; j++) {
          const sA = setIDs[i], sB = setIDs[j];
          for (const primary of [sA, sB]) {
            const secondary = primary === sA ? sB : sA;
            const assign = {};
            for (const key of ALL_SLOT_KEYS) {
              const c = candidates[key].find((x) => x.setID === primary)
                     || candidates[key].find((x) => x.setID === secondary)
                     || null;
              assign[key] = c;
            }
            tryAssign(assign);
          }
        }
      }
    }

    const evalBest = best ? evaluateAssignment(best) : { totals: {} };
    return { assignment: best, score: bestScore, totals: evalBest.totals };
  }

  /* ---- DOM helpers ---- */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
    );
  }

  function imgEl(src, alt, cls) {
    if (!src) return null;
    const i = document.createElement("img");
    i.src = src; i.alt = alt; i.className = cls || "";
    i.onerror = function () { this.style.display = "none"; };
    return i;
  }

  /* Newer assets are texture atlases — obj.frame [x,y,w,h] + obj.sheet [W,H]
     point at the real icon inside the sheet. Render those as a cropped sprite;
     single-frame assets render as a plain <img>. */
  function spriteEl(obj, size, phHtml) {
    if (!obj.img) {
      const ph = document.createElement("div");
      ph.className = "item-thumb-ph";
      ph.innerHTML = phHtml;
      return ph;
    }
    if (obj.frame && obj.sheet) {
      const [x, y, w, h] = obj.frame;
      const [W, H] = obj.sheet;
      const s = size / Math.max(w, h);
      const el = document.createElement("span");
      el.className = "sprite-crop";
      el.style.cssText =
        "display:inline-block;width:" + (w * s).toFixed(1) + "px;height:" + (h * s).toFixed(1) + "px;" +
        "background-image:url('" + obj.img + "');" +
        "background-size:" + (W * s).toFixed(1) + "px " + (H * s).toFixed(1) + "px;" +
        "background-position:-" + (x * s).toFixed(1) + "px -" + (y * s).toFixed(1) + "px;" +
        "background-repeat:no-repeat;";
      return el;
    }
    const i = document.createElement("img");
    i.src = obj.img;
    i.alt = obj.name || "";
    i.onerror = function () { this.outerHTML = '<div class="item-thumb-ph">' + phHtml + "</div>"; };
    return i;
  }

  /* ---- Render ---- */
  function renderAll() {
    const root = document.getElementById("root");
    root.innerHTML = "";

    /* Tab nav */
    const nav = document.createElement("div");
    nav.className = "rift-tabs";
    nav.innerHTML = `
      <button class="rift-tab-btn active" data-tab="gear">My Gear</button>
      <button class="rift-tab-btn" data-tab="optimize">Optimize</button>
      <button class="rift-tab-btn" data-tab="ref">Sets Reference</button>
    `;
    root.appendChild(nav);

    /* Panes */
    const gearPane = document.createElement("div");
    gearPane.id = "tab-gear"; gearPane.className = "rift-pane active";
    root.appendChild(gearPane);

    const optPane = document.createElement("div");
    optPane.id = "tab-optimize"; optPane.className = "rift-pane";
    root.appendChild(optPane);

    const refPane = document.createElement("div");
    refPane.id = "tab-ref"; refPane.className = "rift-pane";
    root.appendChild(refPane);

    nav.addEventListener("click", (e) => {
      const btn = e.target.closest(".rift-tab-btn");
      if (!btn) return;
      nav.querySelectorAll(".rift-tab-btn").forEach((b) => b.classList.remove("active"));
      root.querySelectorAll(".rift-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });

    renderGear(gearPane);
    renderOptimize(optPane);
    renderReference(refPane);
  }

  /* ---- Gear tab ---- */
  function renderGear(container) {
    const totalOwned = totalOwnedPieces();
    const summary = document.createElement("p");
    summary.style.cssText = "font-size:.85rem;color:var(--text-dim);margin:0 0 16px";
    summary.innerHTML = totalOwned === 0
      ? "Set how many of each piece you own — your inventory saves automatically."
      : `<strong style="color:var(--text)">${totalOwned}</strong> piece${totalOwned === 1 ? "" : "s"} owned (duplicates count). Use − / + on each piece.`;
    container.appendChild(summary);

    const grid = document.createElement("div");
    grid.className = "set-grid";
    container.appendChild(grid);

    for (const set of allSets) {
      grid.appendChild(makeSetCard(set));
    }
  }

  function bulkSet(set, n) {
    for (const it of set.items) setQty(it.id, n);
    for (const g of set.gems) setQty(g.id, n);
    /* refresh that card's rows */
    const card = document.querySelector('.set-card[data-set-id="' + set.setID + '"]');
    if (card) {
      card.querySelectorAll(".item-toggle").forEach((row) => {
        const q = getQty(row.dataset.id);
        row.classList.toggle("owned", q > 0);
        const v = row.querySelector(".qty-val");
        if (v) v.textContent = q;
      });
    }
    refreshSetHeader(set);
  }

  function makeSetCard(set) {
    const ownedCount = countOwnedInSet(set);
    const total = set.items.length + set.gems.length;
    const isBar = set.wearer === "Baron";

    const card = document.createElement("div");
    card.className = "set-card " + (isBar ? "baron" : "general");
    card.dataset.setId = set.setID;

    const head = document.createElement("div");
    head.className = "set-card-head";
    head.innerHTML = `
      <span class="set-card-name">${esc(set.name)}</span>
      <span class="wearer-tag">${esc(set.wearer)}</span>
      <button class="set-bulk all">✓ All</button>
      <button class="set-bulk none">✕ None</button>
      <span class="set-count" id="sc-${set.setID}">${ownedCount}/${total}</span>
    `;
    head.querySelector(".set-bulk.all").addEventListener("click", () => bulkSet(set, 1));
    head.querySelector(".set-bulk.none").addEventListener("click", () => bulkSet(set, 0));
    card.appendChild(head);

    const progressWrap = document.createElement("div");
    progressWrap.className = "set-progress";
    const bar = document.createElement("div");
    bar.className = "set-bar";
    bar.id = "sb-" + set.setID;
    bar.style.width = (ownedCount / total * 100) + "%";
    progressWrap.appendChild(bar);
    card.appendChild(progressWrap);

    const itemsGrid = document.createElement("div");
    itemsGrid.className = "set-items-grid";

    for (const item of set.items) {
      itemsGrid.appendChild(makeToggleRow(item, false, set));
    }

    const gemDiv = document.createElement("div");
    gemDiv.className = "gems-divider";
    gemDiv.textContent = "Gem sockets";
    itemsGrid.appendChild(gemDiv);

    for (const gem of set.gems) {
      itemsGrid.appendChild(makeToggleRow(gem, true, set));
    }

    card.appendChild(itemsGrid);
    return card;
  }

  /* Compact emoji-coded stat chips for an item's own effects. */
  function statChips(effects) {
    const chips = [];
    for (const e of effects || []) {
      const cat = effectCategory(e.name);
      if (!cat || !e.value) continue;
      const emoji = CAT_EMOJI[cat.id] || "✨";
      const v = cat.id === "waves" ? "+" + e.value
        : cat.id === "bossSpec" ? "💀" + Number(e.value).toLocaleString()
        : "+" + e.value + (cat.id === "breach" ? "s" : "%");
      chips.push('<span class="stat-chip" title="' + esc(e.label) + '">' + emoji + " " + v + "</span>");
    }
    return chips.length ? '<div class="stat-chips">' + chips.join("") + "</div>" : "";
  }

  function refreshSetHeader(set) {
    const cnt = countOwnedInSet(set);
    const total = set.items.length + set.gems.length;
    const countEl = document.getElementById("sc-" + set.setID);
    const barEl = document.getElementById("sb-" + set.setID);
    if (countEl) countEl.textContent = cnt + "/" + total;
    if (barEl) barEl.style.width = (cnt / total * 100) + "%";
    const summary = document.querySelector("#tab-gear > p");
    if (summary) {
      const n = totalOwnedPieces();
      summary.innerHTML = n === 0
        ? "Set how many of each piece you own — your inventory saves automatically."
        : `<strong style="color:var(--text)">${n}</strong> piece${n === 1 ? "" : "s"} owned (duplicates count). Use − / + on each piece.`;
    }
    updateOwnedLabel();
    const resultsOut = document.getElementById("results-out");
    if (resultsOut && resultsOut.children.length > 0) runAndRenderOptimizer();
  }

  function makeToggleRow(item, isGem, set) {
    const id = String(item.id);
    const slotLabel = isGem ? GEM_LABELS[item.gemType] : item.slot;
    const name = isGem ? (item.name || GEM_LABELS[item.gemType]) : item.name;

    const row = document.createElement("div");
    row.className = "item-toggle" + (getQty(id) > 0 ? " owned" : "");
    row.dataset.id = id;

    const thumbWrap = document.createElement("div");
    thumbWrap.className = "item-thumb-wrap";
    thumbWrap.appendChild(spriteEl(item, 36, isGem ? "💎" : esc(SLOT_EMOJI[item.slot] || "?")));
    row.appendChild(thumbWrap);

    const info = document.createElement("div");
    info.className = "item-toggle-info";
    info.innerHTML = `<span class="item-slot-tag">${esc(slotLabel)}</span><span class="item-name">${esc(name)}</span>` +
      statChips(item.effects);
    row.appendChild(info);

    /* Quantity stepper */
    const stepper = document.createElement("div");
    stepper.className = "qty-stepper";
    stepper.innerHTML =
      '<button class="qty-btn qty-dec">−</button>' +
      '<span class="qty-val">' + getQty(id) + "</span>" +
      '<button class="qty-btn qty-inc">+</button>';
    row.appendChild(stepper);

    function update(delta) {
      setQty(id, getQty(id) + delta);
      stepper.querySelector(".qty-val").textContent = getQty(id);
      row.classList.toggle("owned", getQty(id) > 0);
      refreshSetHeader(set);
    }
    stepper.querySelector(".qty-dec").addEventListener("click", (e) => { e.stopPropagation(); update(-1); });
    stepper.querySelector(".qty-inc").addEventListener("click", (e) => { e.stopPropagation(); update(+1); });
    /* Clicking the row toggles 0 <-> 1 for quick entry */
    row.addEventListener("click", (e) => {
      if (e.target.closest(".qty-stepper")) return;
      update(getQty(id) > 0 ? -getQty(id) : +1);
    });
    return row;
  }

  /* ---- Optimize tab ---- */
  function renderOptimize(container) {
    const presetBtns = Object.entries(PRESETS).map(([k, p]) =>
      '<button class="preset-btn' + (k === curPreset ? " active" : "") + '" data-preset="' + k + '">' + p.label + "</button>"
    ).join("");
    container.innerHTML = `
      <div class="opt-goal">
        <span class="opt-goal-label">Optimize for</span>
        <div class="preset-row" id="preset-row">${presetBtns}</div>
      </div>
      <div class="opt-controls">
        <button class="opt-run-btn" id="run-btn">⚡ Optimize</button>
        <label class="opt-cmdrs">Commanders
          <select id="cmdr-count"><option value="1">1</option><option value="2">2</option><option value="3">3</option></select>
        </label>
        <button class="opt-clear-btn" id="clear-btn">Clear all owned</button>
        <span class="opt-owned-count" id="owned-count-label"></span>
      </div>
      <div id="results-out" class="results-out"></div>
    `;
    updateOwnedLabel();

    document.getElementById("preset-row").addEventListener("click", (e) => {
      const b = e.target.closest(".preset-btn");
      if (!b) return;
      curPreset = b.dataset.preset;
      document.querySelectorAll(".preset-btn").forEach((x) => x.classList.toggle("active", x === b));
      const out = document.getElementById("results-out");
      if (out && out.children.length > 0) runAndRenderOptimizer();
    });
    document.getElementById("cmdr-count").addEventListener("change", () => {
      const out = document.getElementById("results-out");
      if (out && out.children.length > 0) runAndRenderOptimizer();
    });
    document.getElementById("run-btn").addEventListener("click", runAndRenderOptimizer);
    document.getElementById("clear-btn").addEventListener("click", () => {
      if (!confirm("Clear your entire owned inventory?")) return;
      qty = {};
      saveOwned();
      const gearPane = document.getElementById("tab-gear");
      if (gearPane) { gearPane.innerHTML = ""; renderGear(gearPane); }
      updateOwnedLabel();
      document.getElementById("results-out").innerHTML = "";
    });
  }

  function updateOwnedLabel() {
    const el = document.getElementById("owned-count-label");
    if (!el) return;
    const n = totalOwnedPieces();
    el.innerHTML = n === 0
      ? "No pieces owned yet — add them in the Gear tab."
      : `<strong>${n}</strong> piece${n === 1 ? "" : "s"} owned across all sets.`;
  }

  function runAndRenderOptimizer() {
    const out = document.getElementById("results-out");
    if (!out) return;
    updateOwnedLabel();

    if (totalOwnedPieces() === 0) {
      out.innerHTML = `<p class="no-results-hint">You haven't marked any pieces yet.<br>
        <a href="#" onclick="document.querySelector('[data-tab=gear]').click();return false;">Go to My Gear</a> to set what you own.</p>`;
      return;
    }

    /* Build up to N commanders, consuming the owned pool so duplicates matter. */
    const nCmdrs = +(document.getElementById("cmdr-count")?.value || 1);
    const pool = { ...qty };
    const builds = [];
    for (let c = 0; c < nCmdrs; c++) {
      const r = runOptimizer(pool);
      if (!r.assignment || r.score <= 0) break;
      builds.push(r);
      for (const v of Object.values(r.assignment)) {
        if (!v) continue;
        const id = String(v.item ? v.item.id : v.gem.id);
        pool[id] = Math.max(0, (pool[id] || 0) - 1);
      }
    }

    if (!builds.length) {
      out.innerHTML = `<p class="no-results-hint">Could not find a valid combination. Make sure you have at least a few pieces owned.</p>`;
      return;
    }

    let html = `<p class="opt-result-note">Goal: <b>${PRESETS[curPreset].label}</b>` +
      (builds.length > 1 ? ` · ${builds.length} commanders from your pool (duplicates consumed)` : "") + `</p>`;
    builds.forEach((b, i) => {
      html += renderBuild(b, i + 1, builds.length);
    });
    out.innerHTML = html;
  }

  function renderBuild({ assignment, totals }, idx, total) {
    const setCounts = {};
    for (const v of Object.values(assignment)) {
      if (v) setCounts[v.setID] = (setCounts[v.setID] || 0) + 1;
    }

    let html = `<div class="cmdr-build"><h3 class="cmdr-build-h">${total > 1 ? "👑 Commander " + idx : "Recommended Loadout"}</h3>`;
    html += `<table class="loadout-table"><thead><tr>
      <th>Slot</th><th>Item</th><th>Set</th>
    </tr></thead><tbody>`;

    const slotRows = [
      { key: "Armor",    label: "Armor" },
      { key: "Weapon",   label: "Weapon" },
      { key: "Helmet",   label: "Helmet" },
      { key: "Artifact", label: "Artifact" },
      { key: "Hero",     label: "Hero" },
      { key: "gem0",     label: "Socket I" },
      { key: "gem1",     label: "Socket II" },
      { key: "gem2",     label: "Socket III" },
      { key: "gem3",     label: "Socket IV" },
    ];

    for (const { key, label } of slotRows) {
      const val = assignment[key];
      if (!val) {
        html += `<tr><td class="slot-label">${esc(label)}</td><td colspan="2" class="load-empty">— not owned</td></tr>`;
      } else {
        const itemName = val.item
          ? esc(val.item.name)
          : val.gem
          ? esc(val.gem.name || GEM_LABELS[val.gem.gemType])
          : "?";
        const pcs = setCounts[val.setID] || 0;
        html += `<tr>
          <td class="slot-label">${esc(label)}</td>
          <td class="load-item-name">${itemName}</td>
          <td class="load-set-name">${esc(val.set.name)} <span style="color:var(--text-dim)">(${pcs} pcs)</span></td>
        </tr>`;
      }
    }
    html += "</tbody></table>";

    /* ---- Set bonuses breakdown ---- */
    html += `<div class="bonus-section"><h3>Set Bonuses</h3>`;

    const activeSets = Object.keys(setCounts).map((sid) => allSets.find((s) => s.setID === +sid)).filter(Boolean);
    activeSets.sort((a, b) => (setCounts[b.setID] || 0) - (setCounts[a.setID] || 0));

    for (const set of activeSets) {
      const cnt = setCounts[set.setID] || 0;
      const isBar = set.wearer === "Baron";
      html += `<div class="bonus-set-block ${isBar ? "baron" : ""}">
        <div class="bonus-set-name ${isBar ? "baron" : ""}">${esc(set.name)} — ${cnt}/9 pieces</div>
        <ul class="bonus-list">`;
      for (const bonus of set.bonuses) {
        const active = bonus.pieces <= cnt;
        const fxLabels = bonus.effects.map((e) => prettifyLabel(e.label)).join(" · ");
        html += `<li class="${active ? "active" : ""}">
          <span class="bonus-check">${active ? "✓" : "○"}</span>
          <span class="bonus-tier">${bonus.pieces}pc</span>
          <span>${esc(fxLabels || "—")}</span>
        </li>`;
      }
      html += `</ul></div>`;
    }

    html += `</div>`;

    /* ---- Combat stat totals (what the optimizer maximised) ---- */
    const totalRows = [
      { id: "rangeAtk",      label: "Range attack",         unit: "%" },
      { id: "meleeAtk",      label: "Melee attack",         unit: "%" },
      { id: "courtyard",     label: "Courtyard attack",     unit: "%" },
      { id: "waves",         label: "Extra waves",          unit: "" },
      { id: "limit",         label: "Flank/front limit",    unit: "%" },
      { id: "frontFlankStr", label: "Flank/front strength", unit: "%" },
      { id: "breach",        label: "Wall-break delay",     unit: "s" },
      { id: "bossSpec",      label: "Reserve kills",        unit: "" },
    ];
    const shown = totalRows.filter((r) => (totals[r.id] || 0) > 0);
    if (shown.length) {
      html += `<div class="stat-totals">
        <h3>Combat totals</h3>
        <div class="stat-grid">` +
        shown.map((r) =>
          `<div class="stat-cell">
            <div class="stat-cell-val">+${Math.round(totals[r.id])}${r.unit}</div>
            <div class="stat-cell-label">${esc(r.label)}</div>
          </div>`).join("") +
        `</div></div>`;
    }
    html += "</div>";
    return html;
  }

  /* ---- Reference tab ---- */
  function renderReference(container) {
    for (const set of allSets) {
      const isBar = set.wearer === "Baron";
      const block = document.createElement("div");
      block.className = "ref-set" + (isBar ? " baron" : "");

      const head = document.createElement("div");
      head.className = "ref-set-head";
      head.innerHTML = `
        <span class="wearer-tag">${esc(set.wearer)}</span>
        <h3>${esc(set.name)}</h3>
        <span class="ref-toggle-btn">▼</span>
      `;
      block.appendChild(head);

      const body = document.createElement("div");
      body.className = "ref-body";

      /* Items + gems cols */
      const cols = document.createElement("div");
      cols.className = "ref-cols";

      /* Left: items */
      const itemsCol = document.createElement("div");
      itemsCol.innerHTML = `<p class="ref-sub-h">Equipment (5 pieces)</p>`;
      for (const item of set.items) {
        const row = document.createElement("div");
        row.className = "ref-item-row";
        const itemThumb = spriteEl(item, 28, SLOT_EMOJI[item.slot] || "?");
        if (itemThumb.classList.contains("item-thumb-ph")) itemThumb.className = "ref-item-ph";
        row.appendChild(itemThumb);
        const info = document.createElement("div");
        info.className = "ref-item-info";
        info.innerHTML = `<div class="slot-tag">${esc(item.slot)}</div><div class="name">${esc(item.name)}</div>`;
        row.appendChild(info);
        itemsCol.appendChild(row);
      }
      /* Gems */
      itemsCol.innerHTML += `<p class="ref-sub-h" style="margin-top:12px">Gems (4 sockets)</p>`;
      for (const gem of set.gems) {
        const row = document.createElement("div");
        row.className = "ref-item-row";
        {
          const gemThumb = spriteEl(gem, 28, "💎");
          if (gemThumb.classList.contains("item-thumb-ph")) gemThumb.className = "ref-item-ph";
          row.appendChild(gemThumb);
        }
        const info = document.createElement("div");
        info.className = "ref-item-info";
        info.innerHTML = `<div class="slot-tag">${esc(GEM_LABELS[gem.gemType])}</div><div class="name">${esc(gem.name || "—")}</div>`;
        row.appendChild(info);
        itemsCol.appendChild(row);
      }
      cols.appendChild(itemsCol);

      /* Right: bonuses */
      const bonusCol = document.createElement("div");
      bonusCol.innerHTML = `<p class="ref-sub-h">Set Bonuses</p>`;
      const ul = document.createElement("ul");
      ul.className = "ref-bonus-list";
      for (const bonus of set.bonuses) {
        const li = document.createElement("li");
        const fxLines = bonus.effects.map((e) => prettifyLabel(e.label));
        li.innerHTML = `<span class="ref-bonus-pc">${bonus.pieces}</span><span class="ref-bonus-fx">${esc(fxLines.join(" · ") || "—")}</span>`;
        ul.appendChild(li);
      }
      bonusCol.appendChild(ul);
      cols.appendChild(bonusCol);

      body.appendChild(cols);
      block.appendChild(body);
      container.appendChild(block);

      head.addEventListener("click", () => {
        const open = body.classList.toggle("open");
        head.querySelector(".ref-toggle-btn").textContent = open ? "▲" : "▼";
      });
    }
  }

  /* ---- Bootstrap ---- */
  async function init() {
    loadOwned();
    const resp = await fetch(DATA_URL);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    allSets = data.sets;
    renderAll();
  }

  init().catch((e) => {
    const root = document.getElementById("root");
    if (root) root.innerHTML = `<p class="muted">Failed to load rift data: ${esc(e.message)}</p>`;
    console.error(e);
  });
})();
