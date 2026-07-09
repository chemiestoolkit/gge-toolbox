/* Cloudflare Worker: suggestions relay.
 *
 * Keeps your Discord webhook SECRET. The website posts here; this Worker adds the
 * webhook (stored as an encrypted secret, never in the public site) and forwards.
 *
 * ── Setup (free, ~5 min) ─────────────────────────────────────────────────────
 * 1. https://dash.cloudflare.com → Workers & Pages → Create → Worker. Name it
 *    e.g. "toolkit-suggest". Paste this file's contents as the Worker code, Deploy.
 * 2. Worker → Settings → Variables → add a SECRET named DISCORD_WEBHOOK =
 *    your Discord channel's webhook URL (Channel → Edit → Integrations → Webhooks).
 * 3. (Optional but recommended) set ALLOWED_ORIGIN =
 *    https://chemiestoolkit.github.io   — locks the relay to your site.
 * 4. Copy the Worker URL (e.g. https://toolkit-suggest.<you>.workers.dev) and paste
 *    it as SUGGEST_ENDPOINT in assets/js/suggest.js. Done — the webhook stays hidden.
 */

const CORS = (origin) => ({
  "Access-Control-Allow-Origin": origin || "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
});

export default {
  async fetch(request, env) {
    const allow = env.ALLOWED_ORIGIN || "*";
    const cors = CORS(allow);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405, headers: cors });
    if (!env.DISCORD_WEBHOOK) return new Response("Relay not configured", { status: 500, headers: cors });

    if (allow !== "*") {
      const origin = request.headers.get("Origin") || "";
      if (origin && origin !== allow) return new Response("Forbidden", { status: 403, headers: cors });
    }

    // Accept either multipart form (payload_json) or a raw JSON body.
    let payload;
    try {
      const ct = request.headers.get("Content-Type") || "";
      if (ct.includes("application/json")) {
        payload = await request.json();
      } else {
        const form = await request.formData();
        payload = JSON.parse(form.get("payload_json") || "{}");
      }
    } catch (_) {
      return new Response("Bad payload", { status: 400, headers: cors });
    }

    // Sanitise / cap what we forward so the relay can't be used to send arbitrary junk.
    const e = (payload.embeds && payload.embeds[0]) || {};
    const clean = {
      username: "Toolkit Suggestions",
      embeds: [{
        title: String(e.title || "Suggestion").slice(0, 256),
        description: String(e.description || "").slice(0, 1000),
        color: 0xd9b25a,
        footer: { text: "Maxy's Empire Toolkit · suggestions box" },
      }],
    };
    if (!clean.embeds[0].description.trim()) return new Response("Empty", { status: 400, headers: cors });

    const r = await fetch(env.DISCORD_WEBHOOK, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clean),
    });

    return new Response(r.ok ? "ok" : "discord error", {
      status: r.ok ? 200 : 502,
      headers: cors,
    });
  },
};
