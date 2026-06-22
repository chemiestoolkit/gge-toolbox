/* Chemie's VIP Corner — data-viz toolkit.
 *
 * Tiny, dependency-free inline-SVG/HTML widgets so every number gets a crisp
 * visual. Themable via the same CSS vars as the rest of the corner.
 *
 *   GGEv.bar(value, max, {w, color, label})   proportional bar (might/score)
 *   GGEv.level(n, max, {color, hideNum})       segmented level meter (wall/gate…)
 *   GGEv.pips(filled, total, {color})          dot meter (hits left)
 *   GGEv.gauge(pct, {size, color})             radial gauge 0–100 (toughness)
 *
 * Colour helpers: fortColor(n,max) red→gold→green, toughColor(pct) green→red.
 */
window.GGEv = (function () {
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function fortColor(n, max) {
    var p = max > 0 ? n / max : 0;
    return p < 0.34 ? "#e0563f" : p < 0.67 ? "#d9b25a" : "#5fb55f";
  }
  function toughColor(pct) {
    return pct < 34 ? "#5fb55f" : pct < 67 ? "#d9b25a" : "#e0563f";
  }

  // Proportional bar. Returns "<number> ▮▮▮▯" style by default; bare:true for just the track.
  function bar(value, max, opts) {
    opts = opts || {};
    var w = opts.w || 64;
    var pct = max > 0 ? clamp(value / max, 0, 1) : 0;
    var col = opts.color || "var(--gold)";
    var track = '<span class="gv-bar" style="width:' + w + "px\"><span class=\"gv-bar-fill\" style=\"width:" +
      (pct * 100).toFixed(1) + "%;background-color:" + col + '"></span></span>';
    if (opts.bare) return track;
    var lab = opts.label != null ? "<b>" + opts.label + "</b>" : "";
    return '<span class="gv-barwrap">' + track + lab + "</span>";
  }

  // Segmented level meter — `max` segments, `n` lit, coloured by fill ratio.
  function level(n, max, opts) {
    opts = opts || {};
    n = +n || 0; max = max || 10;
    var col = opts.color || fortColor(n, max);
    var segs = "";
    for (var i = 0; i < max; i++) {
      segs += '<i class="' + (i < n ? "on" : "") + '"' + (i < n ? ' style="background-color:' + col + '"' : "") + "></i>";
    }
    var lab = opts.hideNum ? "" : "<b>" + n + "</b>";
    return '<span class="gv-lvl">' + lab + '<span class="gv-seg">' + segs + "</span></span>";
  }

  // Pip / dot meter (e.g. hits left out of 10).
  function pips(filled, total, opts) {
    opts = opts || {};
    var col = opts.color || "var(--good)";
    var s = "";
    for (var i = 0; i < total; i++) s += '<i class="' + (i < filled ? "on" : "") + '"' + (i < filled ? ' style="background-color:' + col + '"' : "") + "></i>";
    return '<span class="gv-pips">' + s + "</span>";
  }

  // Radial gauge, 0–100, number in the middle.
  function gauge(pct, opts) {
    opts = opts || {};
    var size = opts.size || 36;
    pct = clamp(pct, 0, 100);
    var r = 14, c = 2 * Math.PI * r, off = c * (1 - pct / 100);
    var col = opts.color || toughColor(pct);
    return '<svg class="gv-gauge" width="' + size + '" height="' + size + '" viewBox="0 0 36 36" aria-hidden="true">' +
      '<circle cx="18" cy="18" r="' + r + '" fill="none" stroke="var(--bg-elev-2)" stroke-width="4"/>' +
      '<circle cx="18" cy="18" r="' + r + '" fill="none" stroke="' + col + '" stroke-width="4" stroke-linecap="round" ' +
      'stroke-dasharray="' + c.toFixed(1) + '" stroke-dashoffset="' + off.toFixed(1) + '" transform="rotate(-90 18 18)"/>' +
      '<text x="18" y="22" text-anchor="middle" font-size="12" font-weight="700" fill="var(--text)">' + Math.round(pct) + "</text></svg>";
  }

  return { bar: bar, level: level, pips: pips, gauge: gauge, fortColor: fortColor, toughColor: toughColor };
})();
