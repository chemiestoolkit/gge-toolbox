/* ===========================================================================
   Empire Toolbox — tool registry
   The hub is generated from this list. To add a tool: drop a folder under
   /tools/<slug>/ with an index.html, then add an entry here.
   status: "live" | "soon"
   cat:    "calculators" | "simulators" | "rankings" | "overviews"
   =========================================================================== */
window.TOOLS = [
  // ---- Calculators -------------------------------------------------------
  {
    slug: "travel-speed",
    cat: "calculators",
    name: "Attack Speed & Detection",
    desc: "Land time, horse boosts and the exact moment your attack is detected.",
    icon: "🐎",
    status: "live",
    tags: ["travel", "speed", "detection", "horse", "sight", "attack"],
  },
  {
    slug: "wall-limit",
    cat: "calculators",
    name: "Wall & Gate Limit",
    desc: "Maximum wall and gate defence bonus for your castle setup.",
    icon: "🧱",
    status: "soon",
    tags: ["wall", "gate", "defence", "limit"],
  },
  {
    slug: "food-production",
    cat: "calculators",
    name: "Food Production",
    desc: "Net food output and consumption across your empire.",
    icon: "🍖",
    status: "soon",
    tags: ["food", "production", "farms", "consumption"],
  },
  {
    slug: "mead-production",
    cat: "calculators",
    name: "Mead Production",
    desc: "Mead output planning for your relic buildings.",
    icon: "🍺",
    status: "soon",
    tags: ["mead", "production", "relic"],
  },
  {
    slug: "rift-raid-points",
    cat: "calculators",
    name: "Rift Raid Points",
    desc: "Plan the points you can score in the Rift Raid event.",
    icon: "🌀",
    status: "soon",
    tags: ["rift", "raid", "points", "event"],
  },

  // ---- Simulators --------------------------------------------------------
  {
    slug: "battle-simulator",
    cat: "simulators",
    name: "Battle Simulator",
    desc: "Full attack-vs-castle combat sim: waves, tools, commander & castellan.",
    icon: "⚔️",
    status: "soon",
    tags: ["battle", "combat", "waves", "tools", "commander"],
  },
  {
    slug: "hol-simulator",
    cat: "simulators",
    name: "Hall of Legends",
    desc: "Plan HoL upgrade paths and their combat bonuses.",
    icon: "🏛️",
    status: "soon",
    tags: ["hall", "legends", "hol", "upgrades"],
  },
  {
    slug: "layout-editor",
    cat: "simulators",
    name: "Castle Layout Editor",
    desc: "Drag-and-drop planner for your castle building layout.",
    icon: "🏰",
    status: "soon",
    tags: ["layout", "castle", "buildings", "planner"],
  },

  // ---- Rankings & stats --------------------------------------------------
  {
    slug: "rankings",
    cat: "rankings",
    name: "Player & Alliance Rankings",
    desc: "Live might, glory and event rankings for GGE and E4K.",
    icon: "📊",
    status: "soon",
    tags: ["rankings", "leaderboard", "might", "glory", "alliance"],
  },
];
