// Proxy für TronNRG POST /delegate — der Claim-Call kommt aus dem Wallet-
// Kontext (Browser), hier wird er serverseitig an api.tronnrg.com
// weitergeleitet (kein CORS-Risiko, kein API-Key nötig — tx_hash +
// signierte Nachricht sind der Claim-Token).
module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") return res.status(405).json({ ok: false, error: "method not allowed" });
  var body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  var tx = (body.tx_hash || "") + "", to = (body.delegate_to || "") + "", sig = (body.signature || "") + "";
  if (!/^[0-9a-fA-F]{64}$/.test(tx) || !/^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(to) || !/^[0-9a-fA-Fx]{60,}$/.test(sig)) {
    return res.status(400).json({ ok: false, error: "invalid claim" });
  }
  try {
    var r = await fetch("https://api.tronnrg.com/delegate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tx_hash: tx, delegate_to: to, signature: sig })
    });
    var j = await r.json().catch(function() { return null; });
    return res.status(r.status).json(j || { ok: false, error: "empty upstream response" });
  } catch (e) {
    return res.status(502).json({ ok: false, error: "upstream unreachable" });
  }
};
