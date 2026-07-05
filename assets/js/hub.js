/* Maxy's Empire Toolkit — hub renderer.
   Drives the sidebar archive nav + tool grids on the home page (data-page="home")
   and the Tool Browser (data-page="browse", reads ?cat=). No build step. */
(function () {
  // Sidebar destinations — every entry is its own page.
  const NAV = [
    { id: "home",        label: "Home",           icon: "🏰", href: "index.html" },
    { id: "all",         label: "All Tools",      icon: "🗂️", href: "browse.html" },
    { id: "guides",      label: "Guides",         icon: "📖", href: "browse.html?cat=guides" },
    { id: "calculators", label: "Calculators",    icon: "🧮", href: "browse.html?cat=calculators" },
    { id: "simulators",  label: "Simulators",     icon: "⚔️", href: "browse.html?cat=simulators" },
    { id: "overviews",   label: "Overviews",      icon: "👁️", href: "browse.html?cat=overviews" },
    { id: "rankings",    label: "Rankings",       icon: "📊", href: "browse.html?cat=rankings" },
    { id: "misc",        label: "Misc Tools",     icon: "🧰", href: "browse.html?cat=misc" },
    { id: "vip",         label: "Leaders Corner", icon: "🔒", href: "tools/vip/" },
  ];
  const CAT_LABEL = {
    featured: "⭐ Feature Guides",
    guides: "📖 Guides",
    calculators: "🧮 Calculators",
    simulators: "⚔️ Simulators",
    overviews: "👁️ Overviews",
    rankings: "📊 Rankings & Stats",
    misc: "🧰 Misc Tools",
    vip: "🔒 Chemies Leaders Corner",
  };
  const ORDER = ["featured", "guides", "calculators", "simulators", "overviews", "rankings", "misc", "vip"];

  // Curated strip shown on the home page (by slug, in this order).
  const POPULAR = [
    "guide-rift-raid",          // Rift Raid Basics
    "rift-cy-hits",             // Rift Courtyard Calculator
    "wall-break",               // Rift Wall-Break Simulator
    "rift-optimizer",           // Rift Commander Maker
    "guide-commander-building", // Commander Building Guide
    "gacha-sim",                // Gacha Spin Simulator
    "guide-fungal-rift",        // Fungal Rift guide
    "storm-islands",            // Storm Islands Rankings
  ];

  const page = document.body.dataset.page || "home";
  const params = new URLSearchParams(location.search);
  const cat = params.get("cat");
  const activeNav = page === "home" ? "home" : (cat || "all");

  let query = "";
  const navEl = document.getElementById("side-nav");
  const gridHost = document.getElementById("grid-host");
  const searchEl = document.getElementById("search");

  // ---- Sidebar -----------------------------------------------------------
  if (navEl) {
    NAV.forEach((n) => {
      const el = document.createElement("a");
      el.className = "side-link" + (n.id === activeNav ? " active" : "");
      el.href = n.href;
      el.innerHTML = '<span class="si">' + n.icon + "</span><span>" + n.label + "</span>";
      navEl.appendChild(el);
    });
  }

  // Hero "Access Archives" → the Tool Browser
  const heroCta = document.getElementById("hero-cta");
  if (heroCta) heroCta.onclick = () => { location.href = "browse.html"; };

  // ---- Browse heading ------------------------------------------------------
  const browseHead = document.getElementById("browse-title");
  if (browseHead && cat) {
    browseHead.textContent = (CAT_LABEL[cat] || cat).replace(/^[^ ]+ /, "");
  }

  // ---- Grid rendering ------------------------------------------------------
  function matches(t) {
    if (page === "browse" && cat) {
      // Guides window gathers Feature Guides + Guides under one roof.
      if (cat === "guides") {
        if (t.cat !== "guides" && t.cat !== "featured") return false;
      } else if (t.cat !== cat) {
        return false;
      }
    }
    if (!query) return true;
    const hay = (t.name + " " + t.desc + " " + (t.tags || []).join(" ")).toLowerCase();
    // Tokenised AND-match: every word in the query must appear somewhere in the
    // name/desc/tags, so "raid boss", "boss rift", "attack commander gear" all hit
    // (a plain substring match only worked for contiguous phrases).
    return query.split(/\s+/).filter(Boolean).every((w) => hay.includes(w));
  }

  function cardFor(t) {
    const live = t.status === "live";
    const el = document.createElement(live ? "a" : "div");
    el.className = "card" + (live ? "" : " disabled");
    if (live) el.href = t.url || "tools/" + t.slug + "/";
    const art = t.img
      ? '<div class="ico art"><img src="' + t.img + '" alt="" loading="lazy" ' +
        "onerror=\"this.parentNode.classList.remove('art');this.parentNode.textContent='" + t.icon + "'\"></div>"
      : '<div class="ico">' + t.icon + "</div>";
    el.innerHTML =
      art +
      "<h3>" + t.name + "</h3>" +
      "<p>" + t.desc + "</p>" +
      '<span class="badge ' + (live ? "new" : "soon") + '">' + (live ? "Ready" : "Soon") + "</span>";
    return el;
  }

  function render() {
    if (!gridHost) return;
    gridHost.innerHTML = "";

    // Home, no search → curated "Popular" strip instead of a category sweep.
    if (page === "home" && !query) {
      const bySlug = {};
      window.TOOLS.forEach((t) => { bySlug[t.slug] = t; });
      const items = POPULAR.map((s) => bySlug[s]).filter(Boolean);
      const label = document.createElement("div");
      label.className = "section-label";
      label.textContent = "🔥 Popular";
      const grid = document.createElement("div");
      grid.className = "grid";
      items.forEach((t) => grid.appendChild(cardFor(t)));
      gridHost.appendChild(label);
      gridHost.appendChild(grid);
      const cta = document.createElement("a");
      cta.className = "browse-cta";
      cta.href = "browse.html";
      cta.innerHTML = "<span>Browse the full archive</span><span class='arr'>→</span>";
      gridHost.appendChild(cta);
      return;
    }

    const visible = window.TOOLS.filter(matches);
    if (!visible.length) {
      gridHost.innerHTML = '<div class="empty">No tools match “' + query + "”.</div>";
      return;
    }
    const section = (labelText, items) => {
      const label = document.createElement("div");
      label.className = "section-label";
      label.textContent = labelText;
      const grid = document.createElement("div");
      grid.className = "grid";
      items.forEach((t) => grid.appendChild(cardFor(t)));
      gridHost.appendChild(label);
      gridHost.appendChild(grid);
    };
    ORDER.forEach((c) => {
      const items = visible.filter((t) => t.cat === c);
      if (!items.length) return;
      const feat = items.filter((t) => t.feature);
      const rest = items.filter((t) => !t.feature);
      const plain = (CAT_LABEL[c] || c).replace(/^[^ ]+ /, "");
      if (feat.length) section("⭐ Feature " + plain, feat);
      if (rest.length) section(CAT_LABEL[c] || c, rest);
    });
    if (page === "home") {
      const cta = document.createElement("a");
      cta.className = "browse-cta";
      cta.href = "browse.html";
      cta.innerHTML = "<span>Browse the full archive</span><span class='arr'>→</span>";
      gridHost.appendChild(cta);
    }
  }

  if (searchEl) {
    searchEl.addEventListener("input", () => {
      query = searchEl.value.trim().toLowerCase();
      render();
    });
  }

  render();
})();
