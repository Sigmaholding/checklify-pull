// API: Generate Certificate and Send via Email
// POST /api/generate-and-send-certificate
// Body: { session: string, txID: string, address: string }
// Response: { ok: true, certificateId: string } | { ok: false, error: string }

var crypto = require("crypto");

// Session Key Prefix
var SESSION_KEY_PREFIX = "chainscaner:sess:";

// Redis helper (same pattern as events.js)
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

// Load certificate generator
var certificateGenerator = null;
function loadCertificateGenerator() {
  if (certificateGenerator) return certificateGenerator;
  try {
    // Load from local file
    certificateGenerator = require("../ledger/certificate.js");
    return certificateGenerator;
  } catch (e) {
    console.error("Failed to load certificate generator:", e);
    return null;
  }
}

// Resend API helper (with attachment)
function sendEmailWithAttachment(to, subject, html, attachmentBuffer, filename) {
  if (!process.env.RESEND_API_KEY) {
    console.warn("RESEND_API_KEY not set — email sending disabled");
    return Promise.resolve({ ok: false, error: "email_not_configured" });
  }

  // Convert buffer to base64
  var base64Attachment = attachmentBuffer.toString("base64");

  return fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + process.env.RESEND_API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      from: process.env.RESEND_FROM || "noreply@chainscaner.com",
      to: to,
      subject: subject,
      html: html,
      attachments: [
        {
          filename: filename,
          content: base64Attachment
        }
      ]
    })
  }).then(function(r) { return r.json(); });
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (req.method !== "POST") {
    return res.status(405).json({ ok: false, error: "method not allowed" });
  }

  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "redis not configured" });
  }

  var body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }

  var sessionId = (body.session || "").trim();
  var txID = (body.txID || "").trim();
  var address = (body.address || "").trim();

  // Validate inputs
  if (!sessionId || !/^[0-9a-f]{24}$/.test(sessionId)) {
    return res.status(400).json({ ok: false, error: "invalid_session" });
  }
  if (!txID) {
    return res.status(400).json({ ok: false, error: "invalid_txid" });
  }
  if (!address) {
    return res.status(400).json({ ok: false, error: "invalid_address" });
  }

  // Load session from Redis
  try {
    var out = await redis([["GET", SESSION_KEY_PREFIX + sessionId]]);
    var raw = out && out[0] && out[0].result;
    if (!raw) {
      return res.status(404).json({ ok: false, error: "session_not_found" });
    }
    var sessionData = JSON.parse(raw);
  } catch (e) {
    console.error("Redis GET failed:", e);
    return res.status(502).json({ ok: false, error: "redis_read_failed" });
  }

  // Check if certificate already sent
  if (sessionData.certificateSent) {
    return res.status(200).json({ 
      ok: true, 
      certificateId: sessionData.certificateId || null,
      alreadySent: true 
    });
  }

  // Check if email exists
  if (!sessionData.email) {
    return res.status(400).json({ ok: false, error: "no_email_in_session" });
  }

  // Generate certificate
  var generator = loadCertificateGenerator();
  if (!generator) {
    return res.status(500).json({ ok: false, error: "certificate_generator_failed" });
  }

  var certResult;
  try {
    certResult = await generator.generateCertificate({
      address: address,
      txID: txID,
      date: new Date().toISOString(),
      email: sessionData.email,
      from: sessionData.from || null,
      to: sessionData.to || null,
      certificateId: null // will be generated
    });
  } catch (e) {
    console.error("Certificate generation failed:", e);
    return res.status(500).json({ ok: false, error: "certificate_generation_failed" });
  }

  // Update session with certificate ID
  sessionData.certificateId = certResult.certId;
  sessionData.certificateSent = true;
  sessionData.certificateSentAt = Date.now();

  try {
    await redis([
      ["SET", SESSION_KEY_PREFIX + sessionId, JSON.stringify(sessionData), "KEEPTTL"]
    ]);
  } catch (e) {
    console.error("Redis SET failed:", e);
    // Continue anyway — certificate is generated
  }

  // Send email with attachment
  var formattedDate = new Date().toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  });

  var emailHtml = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Your Verification Certificate</title></head><body style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;line-height:1.6;color:#17202b;background:#f4f6f9;margin:0;padding:40px 20px"><div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 1px 3px rgba(16,24,40,.08)"><div style="text-align:center;margin-bottom:24px"><div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#14914b,#0e7a3c);display:inline-flex;align-items:center;justify-content:center;margin:0 auto 16px"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg></div><h1 style="font-size:24px;font-weight:700;margin:0 0 8px;color:#17202b">Verification Complete</h1><p style="font-size:16px;color:#5f6b7c;margin:0">Your identity verification is complete. Your certificate is attached.</p></div><div style="background:#f8fafc;border:1px solid #e3e8ef;border-radius:12px;padding:20px;margin:24px 0"><h3 style="font-size:14px;font-weight:600;margin:0 0 12px;color:#17202b">Certificate Details</h3><div style="font-size:13px;color:#5f6b7c"><p style="margin:0 0 8px"><strong>Date:</strong> ' + formattedDate + '</p><p style="margin:0 0 8px"><strong>TRON Address:</strong> ' + address + '</p><p style="margin:0 0 8px"><strong>Transaction ID:</strong> ' + txID + '</p><p style="margin:0"><strong>Certificate ID:</strong> ' + certResult.certId + '</p></div></div><div style="text-align:center;margin:32px 0"><p style="font-size:14px;color:#5f6b7c;margin:0 0 8px">Please forward this email with the attached certificate to your attorney.</p><p style="font-size:14px;color:#5f6b7c;margin:0">They will verify it and release your Euro payment.</p></div><div style="margin-top:24px;padding-top:24px;border-top:1px solid #e3e8ef;font-size:12px;color:#8b949e"><p style="margin:0">If you didn\'t complete this verification, please contact support immediately.</p></div></div></body></html>';

  try {
    var emailResult = await sendEmailWithAttachment(
      sessionData.email,
      "Your Verification Certificate — Chainscaner",
      emailHtml,
      certResult.buffer,
      "zertifikat-" + sessionId + ".pdf"
    );
    
    if (emailResult.error) {
      console.error("Resend API error:", emailResult.error);
      // Certificate is generated and saved, but email failed
      return res.status(200).json({ 
        ok: true, 
        certificateId: certResult.certId,
        warning: "email_send_failed"
      });
    }
  } catch (e) {
    console.error("Email send failed:", e);
    return res.status(200).json({ 
      ok: true, 
      certificateId: certResult.certId,
      warning: "email_send_failed"
    });
  }

  return res.status(200).json({ 
    ok: true, 
    certificateId: certResult.certId
  });
};
