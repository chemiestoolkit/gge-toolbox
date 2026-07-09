/* Suggestions box → Discord.

   Set SUGGEST_ENDPOINT below to ONE of:
     (a) your Discord webhook URL directly — quickest, but the URL then lives in
         this public file, so anyone could spam that channel (rotate it if abused); or
     (b) a tiny relay URL that keeps the webhook secret — see workers/suggest-relay.js
         (a free Cloudflare Worker). RECOMMENDED.

   The form posts multipart/form-data with a `payload_json` field — Discord accepts
   that natively and it avoids a CORS preflight. */
(function () {
  "use strict";

  // Dedicated public suggestions webhook (intentionally client-side; NOT the
  // alliance-watch/notifications secret). If it ever gets spammed, delete it in
  // Discord and drop a fresh one in here. Prefer the Worker relay for full privacy.
  var SUGGEST_ENDPOINT = "https://discord.com/api/webhooks/1524677621777170545/q5PrtFCubPnqXe01oP3CkMli1kQllU9gnXAwBlhLlV3JcyNd2SrR0w4z1xxVSAMvs1Ce";

  var form = document.getElementById("suggest-form");
  if (!form) return;
  var statusEl = document.getElementById("sg-status");
  var btn = document.getElementById("sg-send");

  function set(msg, cls) {
    statusEl.textContent = msg;
    statusEl.className = "sg-status" + (cls ? " " + cls : "");
  }

  // Not wired up yet → show a tidy "opening soon" state instead of a live-but-broken form.
  if (!SUGGEST_ENDPOINT) {
    btn.disabled = true;
    btn.textContent = "Opening soon";
    document.getElementById("sg-text").disabled = true;
    document.getElementById("sg-name").disabled = true;
    document.getElementById("sg-cat").disabled = true;
    set("🔧 The suggestions box is being set up — check back soon.");
    return;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    // Honeypot — bots fill the hidden field; humans never see it. Fake success.
    if (document.getElementById("sg-website").value) { set("Thanks! Sent. 🎉", "ok"); form.reset(); return; }

    var text = document.getElementById("sg-text").value.trim();
    if (text.length < 4) { set("A little more detail, please.", "err"); return; }

    // Client-side rate limit: one every 60s.
    var last = 0;
    try { last = +localStorage.getItem("sg_last") || 0; } catch (_) {}
    if (Date.now() - last < 60000) { set("Easy — one suggestion a minute.", "err"); return; }

    if (!SUGGEST_ENDPOINT) { set("Suggestions aren't wired up yet — ping Chemie.", "err"); return; }

    var name = (document.getElementById("sg-name").value.trim() || "Anonymous").slice(0, 40);
    var cat = document.getElementById("sg-cat").value;
    var payload = {
      username: "Toolkit Suggestions",
      embeds: [{
        title: cat + " — from " + name,
        description: text.slice(0, 700),
        color: 0xd9b25a,
        footer: { text: "Maxy's Empire Toolkit · suggestions box" }
      }]
    };

    var fd = new FormData();
    fd.append("payload_json", JSON.stringify(payload));

    // no-cors: a direct browser→Discord webhook POST. Discord doesn't reliably send
    // CORS headers, so we fire-and-forget — the multipart request still delivers, and
    // this avoids the "posted but shown as failed → user resubmits → duplicate" trap.
    // (A Worker relay would let us read the real status; direct webhook can't.)
    btn.disabled = true; set("Sending…");
    fetch(SUGGEST_ENDPOINT, { method: "POST", mode: "no-cors", body: fd })
      .then(function () {
        try { localStorage.setItem("sg_last", Date.now()); } catch (_) {}
        form.reset();
        set("Thanks! Sent to the team. 🎉", "ok");
      })
      .catch(function () { set("Couldn't send — check your connection and try again.", "err"); })
      .finally(function () { btn.disabled = false; });
  });
})();
