/* Chemie's VIP Corner — game-asset icon kit.
 *
 * One tiny helper used across every VIP tool. Two kinds of icon:
 *   • vendored PNGs in /assets/icons/ (resources, units, equipment) pulled
 *     once from the GoodGame Empire Wiki — robust, no hotlinking.
 *   • inline SVG glyphs (Lucide paths, ISC) for concepts the wiki has no clean
 *     art for: might, glory, loot, rank medals, kingdom flags, castle, trend.
 *
 * Usage:  GGEi.ic("rubies")            -> <img> for a vendored icon
 *         GGEi.ic("might", 18)         -> <svg> glyph at 18px
 *         GGEi.lab("coins", num(x))    -> icon + text, baseline-aligned
 *         GGEi.medal(1)                -> gold rank medal (1/2/3 only)
 *         GGEi.kingdom(0)              -> colour-coded kingdom flag
 *
 * Game art © Goodgame Studios, via the GoodGame Empire Wiki (Fandom).
 */
window.GGEi = (function () {
  var BASE = "../../assets/icons/";

  // Vendored PNGs that actually exist on disk.
  var IMG = {
    wood: 1, stone: 1, food: 1, coins: 1, rubies: 1, aquamarine: 1, charcoal: 1,
    glass: 1, honey: 1, mead: 1, honor: 1, alliance: 1, equipment: 1,
    crossbowman: 1, maceman: 1, "storm-islands": 1
  };
  // Friendly aliases so call sites can use natural words.
  var ALIAS = {
    aqua: "aquamarine", gold: "coins", coin: "coins", ruby: "rubies",
    troops: "maceman", army: "maceman", ally: "alliance", gear: "equipment", storm: "storm-islands"
  };

  // Lucide glyph paths (stroke uses currentColor so they inherit text colour).
  // fill:true entries are solid shapes instead.
  var GLYPH = {
    might:  { p: '<polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" x2="19" y1="19" y2="13"/><line x1="16" x2="20" y1="16" y2="20"/><line x1="19" x2="21" y1="21" y2="19"/><polyline points="14.5 6.5 18 3 21 3 21 6 17.5 9.5"/><line x1="5" x2="9" y1="14" y2="18"/><line x1="7" x2="4" y1="17" y2="20"/><line x1="3" x2="5" y1="19" y2="21"/>' },
    glory:  { p: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>', fill: true },
    loot:   { p: '<path d="M6 3h12l4 6-10 13L2 9Z"/><path d="M11 3 8 9l4 13 4-13-3-6"/><path d="M2 9h20"/>' },
    shield: { p: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>' },
    castle: { p: '<path d="M22 20v-9H2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2Z"/><path d="M18 11V4H6v7"/><path d="M15 22v-4a3 3 0 0 0-6 0v4"/><path d="M6 4V2"/><path d="M18 4V2"/><path d="M10 4V2"/><path d="M14 4V2"/>' },
    up:     { p: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>' },
    down:   { p: '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>' },
    flame:  { p: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>', fill: true },
    clock:  { p: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>' },
    target: { p: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>' }
  };

  // Kingdoms in GGE map index order (matches the tools' KINGDOMS arrays).
  var KING = [
    { n: "Great Empire", c: "#5fb55f" },
    { n: "Everwinter Glacier", c: "#67c1e8" },
    { n: "Burning Sands", c: "#d6a850" },
    { n: "Fire Peaks", c: "#d9603f" }
  ];

  function px(s) { return s ? s : 16; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function imgTag(name, size, title) {
    size = px(size);
    return '<img class="gi" src="' + BASE + name + '.png" width="' + size + '" height="' + size +
      '" alt="' + esc(name) + '" title="' + esc(title || name) + '" loading="lazy">';
  }
  function svgTag(g, size, title) {
    size = px(size);
    var fill = g.fill ? "currentColor" : "none";
    var stroke = g.fill ? "none" : "currentColor";
    return '<svg class="gsvg" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="' + fill +
      '" stroke="' + stroke + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (title ? "<title>" + esc(title) + "</title>" : "") + g.p + "</svg>";
  }

  function ic(name, size, title) {
    if (!name) return "";
    name = ALIAS[name] || name;
    if (IMG[name]) return imgTag(name, size, title);
    if (GLYPH[name]) return svgTag(GLYPH[name], size, title);
    return "";
  }
  function has(name) { name = ALIAS[name] || name; return !!(IMG[name] || GLYPH[name]); }

  // icon + text on one baseline, e.g. lab("rubies", "1.2M")
  function lab(name, text, size) {
    return '<span class="gi-lab">' + ic(name, size) + "<span>" + text + "</span></span>";
  }

  // Rank medals — only 1/2/3 get one; everything else is "".
  function medal(rank, size) {
    var c = { 1: "#e8c14f", 2: "#cbd3da", 3: "#cd7f4b" }[rank];
    if (!c) return "";
    size = px(size);
    return '<svg class="gsvg medal" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="' + c +
      '" stroke="' + c + '" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<title>#' + rank + '</title><circle cx="12" cy="8" r="6"/>' +
      '<path d="m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526" fill="none"/></svg>';
  }

  // Colour-coded kingdom shield. idx 0..3, or pass a kingdom name.
  function kingdom(idx, size) {
    var k = typeof idx === "number" ? KING[idx]
      : KING.filter(function (x) { return x.n.toLowerCase() === String(idx).toLowerCase(); })[0];
    if (!k) return "";
    var s = px(size);
    return '<svg class="gsvg kshield" width="' + s + '" height="' + s + '" viewBox="0 0 24 24" aria-hidden="true">' +
      "<title>" + esc(k.n) + "</title>" +
      '<path d="M12 2.2l7.5 2.8v5.6c0 4.7-3.3 7.6-7.5 10.4-4.2-2.8-7.5-5.7-7.5-10.4V5z" fill="' + k.c + '" stroke="rgba(0,0,0,.4)" stroke-width="1"/>' +
      '<path d="M12 2.2l7.5 2.8v5.6c0 4.7-3.3 7.6-7.5 10.4z" fill="rgba(0,0,0,.16)"/>' +
      '<path d="M12 2.2l7.5 2.8v1l-7.5-2.6L4.5 6V5z" fill="rgba(255,255,255,.35)"/>' +
      "</svg>";
  }

  return { ic: ic, has: has, lab: lab, medal: medal, kingdom: kingdom, KING: KING, BASE: BASE };
})();
