/* Empire Toolbox — reusable overview engine.
   Renders a searchable, sortable table from a column spec. Used by every
   overview tool so they share behaviour and styling.

   EmpireOverview({
     mount:       element to render into,
     data:        array of row objects,
     columns:     [{ key, label, num?:bool, fmt?:(v,row)=>string, cls?:string }],
     searchKeys:  ['name', ...],
     defaultSort: { key, dir:-1 },     // dir 1 asc, -1 desc
     placeholder: 'Search…'
   })
*/
window.EmpireOverview = function (opts) {
  if (opts.layout === "cards") return cardOverview(opts);
  const { mount, data, columns, searchKeys = ["name"] } = opts;
  let sort = opts.defaultSort || { key: columns[0].key, dir: 1 };
  let query = "";

  // --- toolbar ---
  const bar = document.createElement("div");
  bar.className = "ov-bar";
  const search = document.createElement("label");
  search.className = "search";
  search.innerHTML = '<span class="icon">🔍</span>';
  const input = document.createElement("input");
  input.type = "search";
  input.placeholder = opts.placeholder || "Search…";
  input.autocomplete = "off";
  search.appendChild(input);
  const count = document.createElement("span");
  count.className = "ov-count";
  bar.append(search, count);

  // --- table ---
  const scroll = document.createElement("div");
  scroll.className = "ov-scroll";
  const table = document.createElement("table");
  table.className = "ov";
  const thead = document.createElement("thead");
  const htr = document.createElement("tr");
  columns.forEach((c) => {
    const th = document.createElement("th");
    if (c.num) th.className = "num";
    th.innerHTML = c.label + '<span class="arrow"></span>';
    th.onclick = () => {
      if (sort.key === c.key) sort.dir *= -1;
      else sort = { key: c.key, dir: c.num ? -1 : 1 };
      render();
    };
    th.dataset.key = c.key;
    htr.appendChild(th);
  });
  thead.appendChild(htr);
  const tbody = document.createElement("tbody");
  table.append(thead, tbody);
  scroll.appendChild(table);

  mount.append(bar, scroll);
  input.addEventListener("input", () => { query = input.value.trim().toLowerCase(); render(); });

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function rows() {
    let r = data;
    if (query) r = r.filter((row) => searchKeys.some((k) => String(row[k] || "").toLowerCase().includes(query)));
    const dir = sort.dir, key = sort.key;
    const numeric = columns.find((c) => c.key === key)?.num;
    return [...r].sort((a, b) => {
      const x = a[key], y = b[key];
      if (numeric) return ((+x || 0) - (+y || 0)) * dir;
      return String(x).localeCompare(String(y)) * dir;
    });
  }

  function render() {
    [...htr.children].forEach((th) => {
      th.classList.toggle("sorted", th.dataset.key === sort.key);
      const a = th.querySelector(".arrow");
      a.textContent = th.dataset.key === sort.key ? (sort.dir === 1 ? "▲" : "▼") : "";
    });
    const list = rows();
    count.textContent = list.length + (list.length === 1 ? " entry" : " entries");
    tbody.innerHTML = list
      .map((row) =>
        "<tr>" +
        columns.map((c) => {
          const v = c.fmt ? c.fmt(row[c.key], row) : esc(row[c.key]);
          const cls = (c.num ? "num " : "") + (c.cls || "");
          return '<td class="' + cls.trim() + '">' + v + "</td>";
        }).join("") +
        "</tr>"
      )
      .join("");
  }

  render();
  return { render };
};

/* Card layout: image + title + stat list, with search and a sort dropdown.
   opts.card = { img:(row)=>url|null, title:(row)=>str, corner?:(row)=>str|null,
                 stats:[{label, key, num?, fmt?}], placeholder?:'🎴' }
   opts.sortOptions = [{key,label,num}]  (defaults to card.stats) */
function cardOverview(opts) {
  const { mount, data, card, searchKeys = ["name"] } = opts;
  const sortOptions = opts.sortOptions ||
    card.stats.map((s) => ({ key: s.key, label: s.label, num: s.num }));
  let sort = opts.defaultSort || { key: sortOptions[0].key, dir: sortOptions[0].num ? -1 : 1 };
  let query = "";

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const bar = document.createElement("div");
  bar.className = "ov-bar";
  const search = document.createElement("label");
  search.className = "search";
  search.innerHTML = '<span class="icon">🔍</span>';
  const input = document.createElement("input");
  input.type = "search"; input.placeholder = opts.placeholder || "Search…"; input.autocomplete = "off";
  search.appendChild(input);

  const sortWrap = document.createElement("div");
  sortWrap.className = "ov-sort";
  const sel = document.createElement("select");
  sel.innerHTML = sortOptions.map((o) => '<option value="' + o.key + '">Sort: ' + o.label + "</option>").join("");
  sel.value = sort.key;
  const dirBtn = document.createElement("button");
  const setDirLabel = () => (dirBtn.textContent = sort.dir === 1 ? "▲ Asc" : "▼ Desc");
  setDirLabel();
  sortWrap.append(sel, dirBtn);

  const count = document.createElement("span");
  count.className = "ov-count";
  bar.append(search, sortWrap, count);

  const grid = document.createElement("div");
  grid.className = "ov-cards";
  mount.append(bar, grid);

  input.addEventListener("input", () => { query = input.value.trim().toLowerCase(); render(); });
  sel.addEventListener("change", () => {
    sort.key = sel.value;
    sort.dir = (sortOptions.find((o) => o.key === sel.value) || {}).num ? -1 : 1;
    setDirLabel(); render();
  });
  dirBtn.addEventListener("click", () => { sort.dir *= -1; setDirLabel(); render(); });

  function rows() {
    let r = data;
    if (query) r = r.filter((row) => searchKeys.some((k) => String(row[k] || "").toLowerCase().includes(query)));
    const numeric = sortOptions.find((o) => o.key === sort.key)?.num;
    return [...r].sort((a, b) => {
      const x = a[sort.key], y = b[sort.key];
      if (numeric) return ((+x || 0) - (+y || 0)) * sort.dir;
      return String(x).localeCompare(String(y)) * sort.dir;
    });
  }

  function render() {
    const list = rows();
    count.textContent = list.length + (list.length === 1 ? " entry" : " entries");
    grid.innerHTML = list.map((row) => {
      const url = card.img(row);
      const corner = card.corner ? card.corner(row) : null;
      const thumb = url
        ? '<img loading="lazy" src="' + esc(url) + '" alt="" onerror="this.parentNode.innerHTML=\'<span class=&quot;ph&quot;>' + (card.placeholder || "🎴") + '</span>\'">'
        : '<span class="ph">' + (card.placeholder || "🎴") + "</span>";
      const stats = card.stats.map((s) => {
        const v = s.fmt ? s.fmt(row[s.key], row) : esc(row[s.key]);
        return '<div class="stat"><span class="k">' + esc(s.label) + '</span><span class="v">' + v + "</span></div>";
      }).join("");
      return (
        '<div class="ov-card"><div class="thumb">' +
        (corner ? '<span class="corner">' + esc(corner) + "</span>" : "") +
        thumb + '</div><div class="body"><div class="title">' + esc(card.title(row)) +
        '</div><div class="stats">' + stats + "</div></div></div>"
      );
    }).join("");
  }

  render();
  return { render };
}
