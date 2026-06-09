/* Maxy's Empire Toolkit — shared name corrections.
   Goodgame's own game data contains some misspellings. Map the raw (wrong)
   name to the corrected one here; tools apply this when displaying names.
   Keep keys EXACTLY as they appear in the data. Add new ones as you find them. */
window.GGE_CORRECTIONS = {
  "Masquarade Barel Workshop": "Masquerade Barrel Workshop",
};

/* Apply corrections to a single name (returns the fixed name, or the original). */
window.ggeFixName = function (name) {
  return (window.GGE_CORRECTIONS && window.GGE_CORRECTIONS[name]) || name;
};
