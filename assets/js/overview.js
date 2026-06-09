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
