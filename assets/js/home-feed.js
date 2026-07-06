/* Maxy's Empire Toolkit — homepage feed renderer.
   Renders the What's New changelog, GGS news and the events plan from
   assets/data/site-feed.json so they can be kept current (by hand or by the
   data-refresh GitHub Action) without touching index.html. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function renderChangelog(list) {
    const el = document.getElementById("changelog");
    if (!el || !list) return;
    el.innerHTML = list.map((c) =>
      `<li>
        <span class="cl-date">${esc(c.date)}</span>
        <span class="cl-body"><b>${esc(c.title)}</b> — ${esc(c.body)}</span>
      </li>`).join("");
  }

  function renderMaxyNotes(list) {
    const el = document.getElementById("maxy-notes");
    if (!el) return;
    if (!list || !list.length) {
      el.innerHTML = '<li class="note-empty">No notes yet.</li>';
      return;
    }
    el.innerHTML = list.map((n) =>
      `<li class="note-item">
        <div class="note-head"><span class="note-title">${esc(n.title)}</span><span class="note-date">${esc(n.date)}</span></div>
        <div class="note-body">${esc(n.body)}</div>
      </li>`).join("");
  }

  function renderNews(list, allUrl) {
    const el = document.getElementById("news-list");
    if (!el || !list) return;
    el.innerHTML = list.map((n) =>
      `<li class="news-item">
        <span class="news-date">${esc(n.date)}</span>
        <a class="news-title" href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a>
      </li>`).join("");
    const all = document.getElementById("news-all");
    if (all && allUrl) all.href = allUrl;
  }

  function renderEvents(events) {
    const head = document.getElementById("events-head");
    const grid = document.getElementById("events-grid");
    if (!grid || !events) return;
    if (head && events.month) head.textContent = "📅 Upcoming Events — " + events.month;
    const base = events.iconBase || "";
    grid.innerHTML = (events.items || []).map((ev) => {
      const icon = ev.icon
        ? `<img class="ev-ico" src="${esc(base + ev.icon)}" alt="" loading="lazy"
             onerror="this.outerHTML='<span class=&quot;ev-emoji&quot;>${esc(ev.emoji || "•")}</span>'">`
        : `<span class="ev-emoji">${esc(ev.emoji || "•")}</span>`;
      return `<div class="event-chip">
        <div class="event-chip-name">${icon}${esc(ev.name)}</div>
        <div class="event-chip-dates">${esc(ev.dates)}</div>
      </div>`;
    }).join("");
  }

  /* ---- Calendar view of the events plan ----------------------------------
     Parses each event's "dates" string ("06–09 · 13–16 Jun", "01 · 04 Jun",
     "16 Jun – 17 Jul") into day-of-month sets, draws a Mon-first month grid
     with a colour bar per event per day, and a clickable key that highlights
     one event's days across the calendar. */
  const MONTHS = { january:0, february:1, march:2, april:3, may:4, june:5,
                   july:6, august:7, september:8, october:9, november:10, december:11 };

  function parseDays(dates, dim) {
    const days = new Set();
    for (const seg of String(dates || "").split("·")) {
      const nums = (seg.match(/\d{1,2}/g) || []).map(Number);
      const mons = new Set((seg.match(/[A-Za-z]{3,}/g) || []).map((s) => s.toLowerCase()));
      if (!nums.length) continue;
      let a = nums[0], b = nums.length > 1 ? nums[1] : nums[0];
      if (mons.size > 1 || b < a) b = dim;   // range runs into next month → clamp
      for (let d = Math.max(1, a); d <= Math.min(dim, b); d++) days.add(d);
    }
    return days;
  }

  function renderCalendar(events) {
    const host = document.getElementById("events-cal");
    if (!host || !events) return;
    const m = /^(\w+)\s+(\d{4})$/.exec(events.month || "");
    const now = new Date();
    const year = m ? +m[2] : now.getFullYear();
    const mon = m ? (MONTHS[m[1].toLowerCase()] ?? now.getMonth()) : now.getMonth();
    const dim = new Date(year, mon + 1, 0).getDate();
    const startDow = (new Date(year, mon, 1).getDay() + 6) % 7;  // Monday = 0
    const isThisMonth = now.getFullYear() === year && now.getMonth() === mon;

    const evs = (events.items || []).map((ev, i) => ({
      name: ev.name,
      color: "hsl(" + Math.round((i * 137.508) % 360) + " 62% 55%)",
      days: parseDays(ev.dates, dim),
    }));

    let cells = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
      .map((d) => '<div class="evc-dow">' + d + "</div>").join("");
    for (let i = 0; i < startDow; i++) cells += '<div class="evc-day blank"></div>';
    for (let d = 1; d <= dim; d++) {
      const marks = evs.filter((e) => e.days.has(d));
      cells += '<div class="evc-day' + (isThisMonth && d === now.getDate() ? " today" : "") + '">' +
        '<span class="evc-num">' + d + "</span>" +
        marks.slice(0, 5).map((e) =>
          '<i class="evc-bar" data-ev="' + esc(e.name) + '" style="background:' + e.color + '" title="' + esc(e.name) + '"></i>').join("") +
        (marks.length > 5 ? '<i class="evc-more">+' + (marks.length - 5) + "</i>" : "") +
        "</div>";
    }
    const keys = evs.map((e) =>
      '<button class="evc-key" type="button" data-ev="' + esc(e.name) + '">' +
      '<i style="background:' + e.color + '"></i>' + esc(e.name) + "</button>").join("");

    host.innerHTML = '<div class="evc-grid">' + cells + "</div>" +
      '<div class="evc-keys">' + keys + "</div>" +
      '<div class="evc-hint">Tap an event in the key to highlight its days.</div>';

    host.addEventListener("click", (e) => {
      const k = e.target.closest(".evc-key");
      if (!k) return;
      const name = k.dataset.ev, was = k.classList.contains("sel");
      host.querySelectorAll(".evc-key").forEach((x) => x.classList.remove("sel"));
      host.querySelectorAll(".evc-bar").forEach((b) => b.classList.remove("dim", "hot"));
      if (!was) {
        k.classList.add("sel");
        host.querySelectorAll(".evc-bar").forEach((b) =>
          b.classList.add(b.dataset.ev === name ? "hot" : "dim"));
      }
    });
  }

  // Plan ↔ Calendar switch (plan stays the default).
  const evSwitch = document.getElementById("ev-switch");
  if (evSwitch) {
    evSwitch.addEventListener("click", (e) => {
      const b = e.target.closest(".ev-sw");
      if (!b) return;
      evSwitch.querySelectorAll(".ev-sw").forEach((x) => x.classList.toggle("on", x === b));
      document.getElementById("events-grid").hidden = b.dataset.view !== "plan";
      document.getElementById("events-cal").hidden = b.dataset.view !== "cal";
    });
  }

  fetch("assets/data/site-feed.json?v=" + Date.now())
    .then((r) => r.json())
    .then((d) => {
      renderMaxyNotes(d.maxyNotes);
      renderChangelog(d.changelog);
      renderNews(d.news, d.newsUrl);
      renderEvents(d.events);
      renderCalendar(d.events);
    })
    .catch((e) => console.error("home-feed:", e));
})();
