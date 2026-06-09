# 🛡️ Empire Toolbox

A single hub of **calculators and simulators** for *Goodgame Empire* and
*Empire: Four Kingdoms* — all in one consistent interface, no app to install.

> Live site: _enable GitHub Pages on this repo (Settings → Pages → branch `main` / root)._

## Why

The best community tools are scattered across many sites and authors. Empire
Toolbox brings the interactive ones together in one place, rebuilt natively so
they share a UI, work offline, and can grow over time.

## How it's built

- **No build step.** Plain HTML, CSS and vanilla JS — open `index.html` and it runs.
- **Folder per tool.** Each tool lives in `tools/<slug>/` with its own `index.html`.
- **One registry.** `assets/js/registry.js` is the single source of truth; the hub
  page is generated from it. Adding a tool = add a folder + one registry entry.
- **Shared theme.** `assets/css/theme.css` styles the hub and every tool.

## Add a tool

1. Create `tools/my-tool/index.html` (copy an existing tool as a template).
2. Add an entry to `assets/js/registry.js` with `status: "live"`.

## Tools

| Category    | Tool                         | Status |
| ----------- | ---------------------------- | ------ |
| Calculators | Attack Speed & Detection     | ✅ Live |
| Calculators | Wall & Gate Limit            | 🔜 Planned |
| Calculators | Food / Mead Production        | 🔜 Planned |
| Calculators | Rift Raid Points             | 🔜 Planned |
| Simulators  | Battle Simulator             | 🔜 Planned |
| Simulators  | Hall of Legends              | 🔜 Planned |
| Simulators  | Castle Layout Editor         | 🔜 Planned |
| Rankings    | Player & Alliance Rankings   | 🔜 Planned |

## Credits

See [CREDITS.md](CREDITS.md). Unofficial fan project; not affiliated with Goodgame Studios.

## License

Project code: [MIT](LICENSE). Game assets and data belong to their respective owners.
