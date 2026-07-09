/* Rift Raid Boss Overview */
(function () {
  "use strict";

  const DATA_URL = "./data/rift-bosses.json";
  let bosses = [];
  let curBoss = 0;
  let curLevel = 0; // index into levels[]

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }
  function num(n) { return (n || 0).toLocaleString(); }
  function fmtTime(sec) {
    if (!sec) return "—";
    const m = Math.floor(sec / 60), s = sec % 60;
    return s ? `${m}m ${s}s` : `${m}m`;
  }

  function render() {
    const root = document.getElementById("root");
    root.innerHTML = "";

    /* Wall-break sim cross-link */
    const cta = document.createElement("a");
    cta.className = "sim-cta";
    cta.href = "../wall-break/";
    cta.style.textDecoration = "none";
    cta.innerHTML = `
      <span class="sim-cta-ico">🧱</span>
      <span class="sim-cta-text">
        <b>Rift Wall-Break Simulator</b> — plan your breach.
        <p>Work out how many units and which tools you need to breach a wall segment on a
           given boss/stage, factoring the boss's defensive effects below.</p>
      </span>
      <span class="sim-cta-soon" style="background:var(--accent,#c9a227);color:#1a1a1a">Open →</span>
    `;
    root.appendChild(cta);

    /* Boss tabs */
    const tabs = document.createElement("div");
    tabs.className = "boss-tabs";
    bosses.forEach((b, i) => {
      const t = document.createElement("button");
      t.className = "boss-tab" + (i === curBoss ? " active" : "");
      t.innerHTML = (b.img ? `<img class="boss-tab-art" src="${esc(b.img)}" alt="" loading="lazy"
                       style="width:44px;height:44px;object-fit:contain;border-radius:8px"
                       onerror="this.remove()">` : "") +
                    `<span class="boss-tab-name">${esc(b.name)}</span>
                     <span class="boss-tab-sub">${esc(b.internalName)} · ${b.levels.length} levels</span>`;
      t.addEventListener("click", () => { curBoss = i; curLevel = 0; render(); });
      tabs.appendChild(t);
    });
    root.appendChild(tabs);

    const boss = bosses[curBoss];

    /* Boss header */
    const rarCls = (boss.rarity || "").toLowerCase();
    const head = document.createElement("div");
    head.className = "boss-head";
    head.innerHTML = `
      ${boss.img ? `<img class="boss-head-art" src="${esc(boss.img)}" alt="" loading="lazy"
         style="width:96px;height:96px;object-fit:contain;border-radius:12px;flex:none" onerror="this.remove()">` : ""}
      <div class="boss-head-main">
        <h2>${esc(boss.name)}${boss.rarity ? `<span class="rarity-pill ${rarCls}">${esc(boss.rarity)}</span>` : ""}</h2>
        <p class="boss-desc">${esc(boss.description || "")}</p>
      </div>`;
    head.style.display = "flex";
    head.style.gap = "16px";
    head.style.alignItems = "center";
    root.appendChild(head);

    /* Level pills */
    const levelBar = document.createElement("div");
    levelBar.className = "level-bar";
    levelBar.innerHTML = `<div class="level-bar-label">Boss level</div>`;
    const pills = document.createElement("div");
    pills.className = "level-pills";
    boss.levels.forEach((l, i) => {
      const p = document.createElement("button");
      p.className = "level-pill" + (i === curLevel ? " active" : "");
      p.textContent = l.level;
      p.addEventListener("click", () => { curLevel = i; render(); });
      pills.appendChild(p);
    });
    levelBar.appendChild(pills);
    root.appendChild(levelBar);

    const lvl = boss.levels[curLevel];

    /* Level summary */
    const summary = document.createElement("div");
    summary.className = "level-summary";
    const stats = [
      { label: "Boss health (reserve)", val: num(lvl.reserveTotal) },
      { label: "Courtyard size", val: num(lvl.courtyardSize) },
      { label: "Courtyard melee", val: lvl.courtyardMeleePct + "<small>%</small>" },
      { label: "Wall regen", val: fmtTime(lvl.wallRegenSec) },
      { label: "Min points for reward", val: num(lvl.minPointsForRewards) },
      { label: "Health stages", val: lvl.stages.length },
    ];
    summary.innerHTML = stats.map((s) =>
      `<div class="lvl-stat"><div class="lvl-stat-label">${esc(s.label)}</div><div class="lvl-stat-val">${s.val}</div></div>`
    ).join("");
    root.appendChild(summary);

    /* Stages */
    const stagesHead = document.createElement("div");
    stagesHead.className = "stages-head";
    stagesHead.textContent = `Health stages — ${boss.name} Level ${lvl.level}`;
    root.appendChild(stagesHead);

    const list = document.createElement("div");
    list.className = "stage-list";
    lvl.stages.forEach((st) => list.appendChild(stageCard(st)));
    root.appendChild(list);
  }

  function unitPills(segUnits) {
    if (!segUnits.length) return '<span class="unit-pill">empty</span>';
    return segUnits.map((u) => {
      const cls = u.role === "ranged" ? "ranged" : u.role === "melee" ? "melee" : "";
      return `<span class="unit-pill ${cls}">${esc(u.name)} <b>×${num(u.count)}</b></span>`;
    }).join("");
  }

  function fxList(items, cls) {
    if (!items || !items.length) return `<ul class="fx-list ${cls}"><li class="none">None</li></ul>`;
    return `<ul class="fx-list ${cls}">${items.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>`;
  }

  function stageCard(st) {
    const card = document.createElement("div");
    card.className = "stage-card";
    card.innerHTML = `
      <div class="stage-card-head">
        <span class="stage-hp-badge">${st.health}%</span>
        <span class="stage-hp-bar"><span class="stage-hp-fill" style="width:${st.health}%"></span></span>
        <span class="stage-walltotal">${num(st.wallTotal)} wall units</span>
      </div>
      <div class="stage-body">
        <div>
          <p class="walls-block-h">Wall garrison</p>
          <div class="wall-seg"><span class="wall-seg-name">Left</span><span class="wall-seg-units">${unitPills(st.left)}</span></div>
          <div class="wall-seg"><span class="wall-seg-name">Front</span><span class="wall-seg-units">${unitPills(st.front)}</span></div>
          <div class="wall-seg"><span class="wall-seg-name">Right</span><span class="wall-seg-units">${unitPills(st.right)}</span></div>
        </div>
        <div>
          <p class="fx-block-h">Boss effects this stage</p>
          ${fxList(st.defenderEffects, "defender")}
          ${fxList(st.attackerEffects, "attacker")}
          ${st.highlights && st.highlights.length
            ? `<div class="highlights">${st.highlights.map((h) => `<span class="highlight-chip">${esc(h)}</span>`).join("")}</div>`
            : ""}
        </div>
      </div>`;
    return card;
  }

  fetch(DATA_URL)
    .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then((d) => { bosses = d.bosses; render(); })
    .catch((e) => {
      document.getElementById("root").innerHTML =
        `<p class="muted">Could not load rift boss data: ${esc(e.message)}</p>`;
      console.error(e);
    });
})();
