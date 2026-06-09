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

  let allSets = [];
  let owned = new Set();

  /* ---- State ---- */
  function loadOwned() {
    try {
      const s = localStorage.getItem(STORAGE_KEY);
      if (s) owned = new Set(JSON.parse(s));
    } catch (e) {
      owned = new Set();
    }
  }

  function saveOwned() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...owned]));
  }

  function toggleOwned(id) {
    id = String(id);
    if (owned.has(id)) owned.delete(id);
    else owned.add(id);
    saveOwned();
  }

  function countOwnedInSet(set) {
    let n = 0;
    for (const it of set.items) if (owned.has(String(it.id))) n++;
    for (const g of set.gems) if (owned.has(String(g.id))) n++;
    return n;
  }

  /* ---- Optimizer ---- */
  function buildCandidates() {
    const bySlot = {};
    for (const slot of EQUIP_SLOTS) bySlot[slot] = [];
    const byGem = [[], [], [], []];

    for (const set of allSets) {
      for (const item of set.items) {
        if (owned.has(String(item.id))) bySlot[item.slot].push({ setID: set.setID, item, set });
      }
      for (const gem of set.gems) {
        if (owned.has(String(gem.id))) byGem[gem.gemType].push({ setID: set.setID, gem, set });
      }
    }
    return { bySlot, byGem };
  }

  function scoreAssignment(assignment) {
    /* assignment = { Armor: {setID} | null, Weapon: ..., gem0: ..., gem1: ..., gem2: ..., gem3: ... } */
    const counts = {};
    for (const v of Object.values(assignment)) {
      if (v) counts[v.setID] = (counts[v.setID] || 0) + 1;
    }
    let score = 0;
    for (const [sid, cnt] of Object.entries(counts)) {
      const set = allSets.find((s) => s.setID === +sid);
      if (!set) continue;
      for (const bonus of set.bonuses) {
        if (bonus.pieces <= cnt) score += bonus.pieces; // higher-threshold bonus worth more
      }
    }
    return score;
  }

  function runOptimizer() {
    const { bySlot, byGem } = buildCandidates();
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

    return { assignment: best, score: bestScore };
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
    const totalOwned = owned.size;
    const summary = document.createElement("p");
    summary.style.cssText = "font-size:.85rem;color:var(--text-dim);margin:0 0 16px";
    summary.innerHTML = totalOwned === 0
      ? "Tick each piece you own — your inventory saves automatically in your browser."
      : `<strong style="color:var(--text)">${totalOwned}</strong> piece${totalOwned === 1 ? "" : "s"} owned. Click a piece to toggle.`;
    container.appendChild(summary);

    const grid = document.createElement("div");
    grid.className = "set-grid";
    container.appendChild(grid);

    for (const set of allSets) {
      grid.appendChild(makeSetCard(set));
    }
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
      <span class="set-count" id="sc-${set.setID}">${ownedCount}/${total}</span>
    `;
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

  function makeToggleRow(item, isGem, set) {
    const id = String(item.id);
    const isOwned = owned.has(id);
    const slotLabel = isGem ? GEM_LABELS[item.gemType] : item.slot;
    const name = isGem ? (item.name || GEM_LABELS[item.gemType]) : item.name;

    const row = document.createElement("div");
    row.className = "item-toggle" + (isOwned ? " owned" : "");
    row.dataset.id = id;

    /* Thumbnail */
    const thumbWrap = document.createElement("div");
    thumbWrap.className = "item-thumb-wrap";
    if (item.img) {
      const img = document.createElement("img");
      img.src = item.img; img.alt = name; img.className = "item-thumb";
      img.onerror = function () {
        this.parentNode.innerHTML = `<div class="item-thumb-ph">${isGem ? "💎" : esc(SLOT_EMOJI[item.slot] || "?")}</div>`;
      };
      thumbWrap.appendChild(img);
    } else {
      thumbWrap.innerHTML = `<div class="item-thumb-ph">${isGem ? "💎" : esc(SLOT_EMOJI[item.slot] || "?")}</div>`;
    }
    row.appendChild(thumbWrap);

    /* Info */
    const info = document.createElement("div");
    info.className = "item-toggle-info";
    info.innerHTML = `<span class="item-slot-tag">${esc(slotLabel)}</span><span class="item-name">${esc(name)}</span>`;
    row.appendChild(info);

    /* Toggle button */
    const btn = document.createElement("button");
    btn.className = "own-btn";
    btn.title = isOwned ? "Remove" : "Mark as owned";
    btn.textContent = isOwned ? "✓" : "+";
    row.appendChild(btn);

    function toggle() {
      toggleOwned(id);
      const nowOwned = owned.has(id);
      row.classList.toggle("owned", nowOwned);
      btn.textContent = nowOwned ? "✓" : "+";
      btn.title = nowOwned ? "Remove" : "Mark as owned";
      /* Update set count + bar */
      const cnt = countOwnedInSet(set);
      const total = set.items.length + set.gems.length;
      const countEl = document.getElementById("sc-" + set.setID);
      const barEl = document.getElementById("sb-" + set.setID);
      if (countEl) countEl.textContent = cnt + "/" + total;
      if (barEl) barEl.style.width = (cnt / total * 100) + "%";
      /* Update gear tab summary */
      const summary = document.querySelector("#tab-gear > p");
      if (summary) {
        const n = owned.size;
        summary.innerHTML = n === 0
          ? "Tick each piece you own — your inventory saves automatically in your browser."
          : `<strong style="color:var(--text)">${n}</strong> piece${n === 1 ? "" : "s"} owned. Click a piece to toggle.`;
      }
      updateOwnedLabel();
      /* Re-run optimizer if results are showing */
      const resultsOut = document.getElementById("results-out");
      if (resultsOut && resultsOut.children.length > 0) runAndRenderOptimizer();
    }

    row.addEventListener("click", (e) => { if (e.target !== btn) toggle(); });
    btn.addEventListener("click", (e) => { e.stopPropagation(); toggle(); });
    return row;
  }

  /* ---- Optimize tab ---- */
  function renderOptimize(container) {
    container.innerHTML = `
      <div class="opt-controls">
        <button class="opt-run-btn" id="run-btn">⚡ Optimize</button>
        <button class="opt-clear-btn" id="clear-btn">Clear all owned</button>
        <span class="opt-owned-count" id="owned-count-label"></span>
      </div>
      <div id="results-out" class="results-out"></div>
    `;
    updateOwnedLabel();

    document.getElementById("run-btn").addEventListener("click", runAndRenderOptimizer);
    document.getElementById("clear-btn").addEventListener("click", () => {
      if (!confirm("Clear your entire owned inventory?")) return;
      owned.clear();
      saveOwned();
      /* Re-render gear tab toggles */
      const gearPane = document.getElementById("tab-gear");
      if (gearPane) { gearPane.innerHTML = ""; renderGear(gearPane); }
      updateOwnedLabel();
      document.getElementById("results-out").innerHTML = "";
    });
  }

  function updateOwnedLabel() {
    const el = document.getElementById("owned-count-label");
    if (!el) return;
    const n = owned.size;
    el.innerHTML = n === 0
      ? "No pieces owned yet — add them in the Gear tab."
      : `<strong>${n}</strong> piece${n === 1 ? "" : "s"} owned across all sets.`;
  }

  function runAndRenderOptimizer() {
    const out = document.getElementById("results-out");
    if (!out) return;
    updateOwnedLabel();

    if (owned.size === 0) {
      out.innerHTML = `<p class="no-results-hint">You haven't marked any pieces yet.<br>
        <a href="#" onclick="document.querySelector('[data-tab=gear]').click();return false;">Go to My Gear</a> to tick off what you own.</p>`;
      return;
    }

    const { assignment, score } = runOptimizer();

    if (!assignment || score < 0) {
      out.innerHTML = `<p class="no-results-hint">Could not find a valid combination. Make sure you have at least a few pieces owned.</p>`;
      return;
    }

    /* Build set piece counts from assignment */
    const setCounts = {};
    for (const v of Object.values(assignment)) {
      if (v) setCounts[v.setID] = (setCounts[v.setID] || 0) + 1;
    }

    /* ---- Loadout table ---- */
    let html = "<h3 style='font-size:.85rem;text-transform:uppercase;letter-spacing:.06em;color:var(--text-dim);margin:0 0 12px'>Recommended Loadout</h3>";
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
    html += `<p class="score-line">Optimizer score: <strong>${score}</strong> bonus-tier points.</p>`;

    out.innerHTML = html;
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
        if (item.img) {
          const img = document.createElement("img");
          img.src = item.img; img.alt = item.name;
          img.onerror = function () { this.outerHTML = `<div class="ref-item-ph">${SLOT_EMOJI[item.slot] || "?"}</div>`; };
          row.appendChild(img);
        } else {
          const ph = document.createElement("div");
          ph.className = "ref-item-ph";
          ph.textContent = SLOT_EMOJI[item.slot] || "?";
          row.appendChild(ph);
        }
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
        if (gem.img) {
          const img = document.createElement("img");
          img.src = gem.img; img.alt = gem.name;
          img.onerror = function () { this.outerHTML = `<div class="ref-item-ph">💎</div>`; };
          row.appendChild(img);
        } else {
          const ph = document.createElement("div");
          ph.className = "ref-item-ph"; ph.textContent = "💎";
          row.appendChild(ph);
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
