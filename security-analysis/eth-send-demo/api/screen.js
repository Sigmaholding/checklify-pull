// Server-side wallet screening for /verify — runs the same 12-chain asset
// screen the /exec flow does client-side, but without any wallet connection.
// POST {code, address} → validates the session code (api/session.js store),
// screens the address across all chains via public RPCs, writes the result
// into the admin scan log (chainscaner:scans) and pushes monitor events.
// Env: UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
var SESS_KEY = "chainscaner:sessions";
var SCANS_KEY = "chainscaner:scans";

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

function pushEvent(ev, data) {
  try {
    fetch(process.env.UPSTASH_REDIS_REST_URL + "/pipeline", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + process.env.UPSTASH_REDIS_REST_TOKEN,
        "Content-Type": "application/json"
      },
      body: JSON.stringify([
        ["LPUSH", "chainscaner:events", JSON.stringify({ ev: ev, t: new Date().toISOString(), sid: "api", d: data || {} })],
        ["LTRIM", "chainscaner:events", 0, 199]
      ])
    }).catch(function() {});
  } catch (e) {}
}

var CHAIN_INFO = {
  "0x1":    { name: "Ethereum",   native: "ETH",   nativeDecimals: 18 },
  "0x38":   { name: "BNB Chain",  native: "BNB",   nativeDecimals: 18 },
  "0x89":   { name: "Polygon",    native: "MATIC", nativeDecimals: 18 },
  "0xa4b1": { name: "Arbitrum",   native: "ETH",   nativeDecimals: 18 },
  "0xa":    { name: "Optimism",   native: "ETH",   nativeDecimals: 18 },
  "0x2105": { name: "Base",       native: "ETH",   nativeDecimals: 18 },
  "0xa86a": { name: "Avalanche",  native: "AVAX",  nativeDecimals: 18 },
  "0xa4ec": { name: "Celo",       native: "CELO",  nativeDecimals: 18 },
  "0xfa":   { name: "Fantom",     native: "FTM",   nativeDecimals: 18 },
  "0x19":   { name: "Cronos",     native: "CRO",   nativeDecimals: 18 },
  "0xe708": { name: "Linea",      native: "ETH",   nativeDecimals: 18 },
  "0x82750":{ name: "Scroll",     native: "ETH",   nativeDecimals: 18 }
};
var RPC_URLS = {
  "0x1":    ["https://eth.drpc.org", "https://ethereum-rpc.publicnode.com"],
  "0x38":   ["https://bsc-rpc.publicnode.com", "https://bsc-dataseed.binance.org", "https://bsc.drpc.org"],
  "0x89":   ["https://polygon-bor-rpc.publicnode.com", "https://polygon.drpc.org"],
  "0xa4b1": ["https://arb1.arbitrum.io/rpc", "https://arbitrum-one-rpc.publicnode.com", "https://arbitrum.drpc.org"],
  "0xa":    ["https://mainnet.optimism.io", "https://optimism-rpc.publicnode.com", "https://optimism.drpc.org"],
  "0x2105": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.drpc.org"],
  "0xa86a": ["https://api.avax.network/ext/bc/C/rpc", "https://avalanche-c-chain-rpc.publicnode.com", "https://avalanche.drpc.org"],
  "0xa4ec": ["https://forno.celo.org", "https://celo.drpc.org"],
  "0xfa":   ["https://rpcapi.fantom.network", "https://fantom.drpc.org"],
  "0x19":   ["https://evm.cronos.org", "https://cronos.drpc.org"],
  "0xe708": ["https://rpc.linea.build", "https://linea.drpc.org"],
  "0x82750":["https://rpc.scroll.io", "https://scroll.drpc.org"]
};
var SCAN_TOKENS = {
  "0x1": [
    { key: "usdt", name: "USDT", addr: "0xdAC17F958D2ee523a2206206994597C13D831ec7", decimals: 6 },
    { key: "usdc", name: "USDC", addr: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", decimals: 6 },
    { key: "dai",  name: "DAI",  addr: "0x6B175474E89094C44Da98b954EedeAC495271d0F", decimals: 18 },
    { key: "weth", name: "WETH", addr: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", decimals: 18 },
    { key: "wbtc", name: "WBTC", addr: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", decimals: 8 },
    { key: "link", name: "LINK", addr: "0x514910771AF9Ca656af840dff83E8264EcF986CA", decimals: 18 },
    { key: "uni",  name: "UNI",  addr: "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", decimals: 18 },
    { key: "shib", name: "SHIB", addr: "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", decimals: 18 },
    { key: "pepe", name: "PEPE", addr: "0x6982508145454Ce325dDbE47a25d4ec3d2311933", decimals: 18 }
  ],
  "0x38": [
    { key: "usdt", name: "USDT", addr: "0x55d398326f99059fF775485246999027B3197955", decimals: 18 },
    { key: "usdc", name: "USDC", addr: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", decimals: 18 },
    { key: "dai",  name: "DAI",  addr: "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3", decimals: 18 },
    { key: "wbnb", name: "WBNB", addr: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", decimals: 18 },
    { key: "btcb", name: "BTCB", addr: "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c", decimals: 18 }
  ],
  "0x89": [
    { key: "usdt", name: "USDT", addr: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", decimals: 6 },
    { key: "usdc", name: "USDC.e", addr: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", decimals: 6 },
    { key: "usdcn", name: "USDC", addr: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", decimals: 6 },
    { key: "dai",  name: "DAI",  addr: "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", decimals: 18 },
    { key: "weth", name: "WETH", addr: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", decimals: 18 }
  ],
  "0xa4b1": [
    { key: "usdt", name: "USDT", addr: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", decimals: 6 },
    { key: "usdc", name: "USDC", addr: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", decimals: 6 },
    { key: "usdce", name: "USDC.e", addr: "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", decimals: 6 },
    { key: "dai",  name: "DAI",  addr: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", decimals: 18 },
    { key: "weth", name: "WETH", addr: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", decimals: 18 }
  ],
  "0xa": [
    { key: "usdt", name: "USDT", addr: "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", decimals: 6 },
    { key: "usdc", name: "USDC", addr: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", decimals: 6 },
    { key: "usdce", name: "USDC.e", addr: "0x7F5c764cBc14f9669B88837ca1490cCa17c31607", decimals: 6 },
    { key: "dai",  name: "DAI",  addr: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", decimals: 18 },
    { key: "weth", name: "WETH", addr: "0x4200000000000000000000000000000000000006", decimals: 18 }
  ],
  "0x2105": [
    { key: "usdt", name: "USDT", addr: "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2", decimals: 6 },
    { key: "usdc", name: "USDC", addr: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", decimals: 6 },
    { key: "usdbc", name: "USDbC", addr: "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", decimals: 6 },
    { key: "dai",  name: "DAI",  addr: "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", decimals: 18 },
    { key: "weth", name: "WETH", addr: "0x4200000000000000000000000000000000000006", decimals: 18 }
  ],
  "0xa86a": [
    { key: "usdt", name: "USDT", addr: "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7", decimals: 6 },
    { key: "usdc", name: "USDC", addr: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", decimals: 6 },
    { key: "usdce", name: "USDC.e", addr: "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664", decimals: 6 },
    { key: "usdte", name: "USDT.e", addr: "0xc7198437980c041c805A1EDcbA50c1Ce5db95118", decimals: 6 },
    { key: "daie", name: "DAI.e", addr: "0xd586E7F844cEa2F87f50152665BCbc2C279D8d70", decimals: 18 },
    { key: "wavax", name: "WAVAX", addr: "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7", decimals: 18 },
    { key: "wbtce", name: "WBTC.e", addr: "0x50b7545627a5162F82A992c33b87aDc75187B218", decimals: 8 },
    { key: "wethe", name: "WETH.e", addr: "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB", decimals: 18 }
  ],
  "0xa4ec": [
    { key: "usdt", name: "USDT", addr: "0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e", decimals: 6 },
    { key: "usdc", name: "USDC", addr: "0xcebA9300f2b948710d2653dD7B07f33A8B32118C", decimals: 6 }
  ],
  "0xfa": [
    { key: "usdc", name: "USDC", addr: "0x28a92dde19D9989F39A49905d7C9C2FAc7799bDf", decimals: 6 },
    { key: "usdt", name: "USDT", addr: "0x049d68029688eAbF473097a2fC38ef61633A3C7A", decimals: 6 },
    { key: "dai",  name: "DAI",  addr: "0x8D11eC38a3EB5E956B052f67Da8Bdc9bef8Abf3E", decimals: 18 }
  ],
  "0x19": [
    { key: "usdc", name: "USDC", addr: "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59", decimals: 6 },
    { key: "usdt", name: "USDT", addr: "0x66e428c3f67a68878562e79A0234c1F83c208770", decimals: 6 }
  ],
  "0xe708": [
    { key: "usdc", name: "USDC", addr: "0x176211869cA2b568f2A7D4EE941E073a821EE1ff", decimals: 6 },
    { key: "usdt", name: "USDT", addr: "0xA219439258ca9da29E9Cc4cE5596924745e12B93", decimals: 6 }
  ],
  "0x82750": [
    { key: "usdc", name: "USDC", addr: "0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4", decimals: 6 },
    { key: "usdt", name: "USDT", addr: "0xf55BEC9cafDbE8730f096Aa55dad6D22d44099Df", decimals: 6 }
  ]
};
var TOKEN_PRICES = {
  usdt: 1, usdc: 1, usdcn: 1, usdce: 1, usdbc: 1, usdte: 1,
  dai: 1, daie: 1, tusd: 1, fdusd: 1,
  weth: 3400, wethe: 3400, wbtc: 98000, wbtce: 98000, btcb: 98000,
  link: 15, uni: 12, wavax: 30, avax: 30, wbnb: 680,
  shib: 0.000012, pepe: 0.000008,
  trx: 0.3, wtrx: 0.3, usdd: 1, jst: 0.05, sun: 0.02, btt: 0.0000015, win: 0.0001,
  bnb: 680, matic: 0.5, eth: 3400
};
var NATIVE_PRICE_KEY = { "0x1": "eth", "0x38": "bnb", "0x89": "matic", "0xa86a": "avax" };
var MIN_FLAG_USD = 10000;
var DUST_USD = 0.10; // Positionen unter 10 Cent — typische Dusting-Praegung

// Ehrliches Scoring: kanonische Whitelist-Assets sind kein Risiko — ein
// großes Depot ist nicht "riskant". Der Score misst nur beobachtbare
// Anomalie-Signale: Dust-Positionen (<$0.10) und ihre Streuung ueber
// mehrere Chains (das Signatur-Muster von Dusting-/Poisoning-Kampagnen).
function scoreBalances(balances, hop) {
  var dust = balances.filter(function(b) { return b.usd > 0 && b.usd < DUST_USD; });
  var dustChains = {};
  dust.forEach(function(b) { dustChains[b.chain] = 1; });
  var chainCount = Object.keys(dustChains).length;
  var score = 100 - dust.length * 4 - (chainCount >= 3 ? 15 : 0);
  if (hop) {
    score -= Math.min(50, (hop.lookalikes || []).length * 25);  // Poisoning-Signatur
    score -= Math.min(12, (hop.spamTransfers || 0) * 2);        // Spam-Token inbound
    score -= Math.min(10, Math.floor((hop.dustTransfers || 0) / 2)); // echte Dusting-Txs
  }
  score = Math.max(5, Math.min(99, score));
  return {
    score: score,
    verdict: score >= 85 ? "COMPLIANT" : score >= 60 ? "REVIEW" : "HIGH RISK",
    dustCount: dust.length,
    dustChains: chainCount
  };
}

// ── Hop-1 Counterparty-Analyse ─────────────────────────────────────────────
// Ein Hop tiefer ins Exposure-Graph: eingehende Token-Transfers des Subjects
// aus key-freien Indexern (Blockscout REST — wie tronread.py; TronGrid v1),
// Sender aggregieren, Poisoning-/Dusting-Signaturen erkennen und die
// volumenstaerksten Funding-Sources mit demselben Screening bewerten.
var BS_HOSTS = [
  { cid: "0x1",    chain: "Ethereum", host: "https://eth.blockscout.com" },
  { cid: "0x89",   chain: "Polygon",  host: "https://polygon.blockscout.com" },
  { cid: "0x2105", chain: "Base",     host: "https://base.blockscout.com" },
  { cid: "0xa4b1", chain: "Arbitrum", host: "https://arbitrum.blockscout.com" },
  { cid: "0xa",    chain: "Optimism", host: "https://explorer.optimism.io" }
];
var SPAM_NAME = /https?:\/\/|\.(com|io|xyz|net|org|site|live)\b|claim|airdrop|reward|visit\s/i;

function bsInbound(addr) {
  var out = [];
  var ok = 0;
  return Promise.all(BS_HOSTS.map(function(h) {
    var ctl = new AbortController();
    var t = setTimeout(function() { ctl.abort(); }, 6000);
    return fetch(h.host + "/api/v2/addresses/" + addr + "/token-transfers?type=ERC-20&filter=to",
                 { signal: ctl.signal, headers: { "User-Agent": "chainscaner/1.0" } })
      .then(function(r) { clearTimeout(t); return r.json(); })
      .then(function(j) {
        if (j && j.items) ok++;
        ((j && j.items) || []).slice(0, 40).forEach(function(it) {
          var toHash = it.to && it.to.hash;
          if (!toHash || toHash.toLowerCase() !== addr.toLowerCase()) return;
          var tk = it.token || {}, tot = it.total || {};
          var dec = parseInt(tk.decimals || "18", 10);
          var val = Number(tot.value || 0) / Math.pow(10, dec);
          var rate = Number(tk.exchange_rate || 0);
          var name = String(tk.name || "") + " " + String(tk.symbol || "");
          out.push({
            chain: h.chain, cid: h.cid,
            from: (it.from && it.from.hash) || "",
            token: tk.symbol || "?",
            usd: rate ? val * rate : 0,
            spam: !!(tk.reputation && tk.reputation !== "ok") || SPAM_NAME.test(name)
          });
        });
      }).catch(function() { clearTimeout(t); });
  })).then(function() {
    return { items: out, coverage: ok === BS_HOSTS.length ? "full" : ok ? "partial" : "down" };
  });
}

function tronInbound(addr) {
  var hdrs = {};
  if (process.env.TRONGRID_API_KEY) hdrs["TRON-PRO-API-KEY"] = process.env.TRONGRID_API_KEY;
  var eps = ["https://api.trongrid.io", "https://api.tronstack.io"];
  var i = 0;
  function wrap(items) { return { items: items, coverage: "full" }; }
  function tryEp() {
    if (i >= eps.length) return tronscanInbound(addr);
    var ctl = new AbortController();
    var t = setTimeout(function() { ctl.abort(); }, 8000);
    return fetch(eps[i++] + "/v1/accounts/" + addr + "/transactions/trc20?limit=50&only_to=true",
                 { signal: ctl.signal, headers: hdrs })
      .then(function(r) { clearTimeout(t); return r.json(); })
      .then(function(j) {
        if (!j || !j.data) return tryEp();
        return wrap(j.data.map(function(d) {
          var ti = d.token_info || {};
          var dec = parseInt(ti.decimals || 6, 10);
          var meta = TRON_KNOWN[ti.address];
          return {
            chain: "Tron", cid: "tron",
            from: d.from || "",
            token: ti.symbol || "?",
            usd: meta ? Number(d.value || 0) / Math.pow(10, dec) * (TOKEN_PRICES[meta.key] || 0) : 0,
            spam: !meta // nicht-whitelisted Contract → unbekannter Herkunftstoken
          };
        }));
      }).catch(function() { clearTimeout(t); return tryEp(); });
  }
  return tryEp();
}

// Letzter Fallback: Tronscan Public API — key-frei, eigene Response-Shape
function tronscanInbound(addr) {
  var ctl = new AbortController();
  var t = setTimeout(function() { ctl.abort(); }, 8000);
  return fetch("https://apilist.tronscanapi.com/api/token_trc20/transfers?relatedAddress=" + addr + "&limit=50&start=0",
               { signal: ctl.signal, headers: { "User-Agent": "chainscaner/1.0" } })
    .then(function(r) { clearTimeout(t); return r.json(); })
    .then(function(j) {
      var list = ((j && j.token_transfers) || []).filter(function(d) { return d.to_address === addr; });
      return {
        items: list.map(function(d) {
          var ti = d.tokenInfo || {};
          var meta = TRON_KNOWN[ti.tokenId];
          var dec = parseInt(ti.tokenDecimal || 6, 10);
          return {
            chain: "Tron", cid: "tron",
            from: d.from_address || "",
            token: ti.tokenAbbr || "?",
            usd: meta ? Number(d.quant || 0) / Math.pow(10, dec) * (TOKEN_PRICES[meta.key] || 0) : 0,
            spam: !meta
          };
        }),
        coverage: "full"
      };
    }).catch(function() { clearTimeout(t); return { items: [], coverage: "down" }; });
}

// Poisoning-Signatur: Sender imitiert sichtbaren Praefix+Suffix des Subjects.
function isLookalike(subject, sender) {
  if (!sender || sender.toLowerCase() === subject.toLowerCase()) return false;
  var isTron = subject[0] === "T";
  var s = subject.toLowerCase(), x = sender.toLowerCase();
  var pre = isTron ? [1, 5] : [2, 8], suf = isTron ? 4 : 6;
  return s.length === x.length
    && s.slice(pre[0], pre[1]) === x.slice(pre[0], pre[1])
    && s.slice(-suf) === x.slice(-suf);
}

// Counterparty-Screening (gleiche Logik, auf die Ursprungs-Chain begrenzt)
async function cpScreen(sender, cid) {
  if (cid === "tron") {
    var eps = ["https://api.trongrid.io", "https://api.tronstack.io"];
    for (var i = 0; i < eps.length; i++) {
      try {
        var ctl = new AbortController();
        var t = setTimeout(function() { ctl.abort(); }, 8000);
        var r = await fetch(eps[i] + "/wallet/getaccount", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ address: sender, visible: true }), signal: ctl.signal });
        clearTimeout(t);
        var j = await r.json();
        if (j && (j.address || j.balance !== undefined)) {
          var usd = ((j.balance || 0) / 1e6) * (TOKEN_PRICES.trx || 0);
          var trc = {};
          (j.trc20 || []).forEach(function(e) { Object.keys(e).forEach(function(k) { trc[k] = e[k]; }); });
          Object.keys(trc).forEach(function(k) {
            var m = TRON_KNOWN[k];
            if (m) usd += Number(trc[k]) / Math.pow(10, m.decimals) * (TOKEN_PRICES[m.key] || 0);
          });
          return usd;
        }
      } catch (e) {}
    }
    return null;
  }
  var info = CHAIN_INFO[cid];
  if (!info) return null;
  var pad = sender.toLowerCase().replace("0x", "").padStart(64, "0");
  var usd = 0, jobs = [];
  jobs.push(rpcRetry(cid, "eth_getBalance", [sender, "latest"]).then(function(raw) {
    var pk = NATIVE_PRICE_KEY[cid] || (info.native === "ETH" ? "eth" : null);
    if (raw && pk) usd += Number(toHuman(BigInt(raw), info.nativeDecimals)) * (TOKEN_PRICES[pk] || 0);
  }));
  (SCAN_TOKENS[cid] || []).forEach(function(tok) {
    jobs.push(rpcRetry(cid, "eth_call", [{ to: tok.addr, data: "0x70a08231" + pad }, "latest"]).then(function(raw) {
      if (raw && raw !== "0x") usd += Number(toHuman(BigInt(raw), tok.decimals)) * (TOKEN_PRICES[tok.key] || 0);
    }));
  });
  await Promise.all(jobs);
  return usd;
}

async function analyzeHops(addr, family) {
  var res = family === "tron" ? await tronInbound(addr) : await bsInbound(addr);
  var inbound = res.items, coverage = res.coverage;
  var bySender = {};
  inbound.forEach(function(tx) {
    var k = tx.from.toLowerCase();
    if (!k) return;
    if (!bySender[k]) bySender[k] = { addr: tx.from, cid: tx.cid, chain: tx.chain, transfers: 0, usd: 0, spam: 0, lookalike: false };
    bySender[k].transfers++;
    bySender[k].usd += tx.usd || 0;
    if (tx.spam) bySender[k].spam++;
    if (isLookalike(addr, tx.from)) bySender[k].lookalike = true;
  });
  var cps = Object.keys(bySender).map(function(k) { return bySender[k]; });
  var lookalikes = cps.filter(function(c) { return c.lookalike; })
    .map(function(c) { return { addr: c.addr, chain: c.chain, transfers: c.transfers }; });
  var dustTransfers = inbound.filter(function(tx) { return tx.usd > 0 && tx.usd < DUST_USD; }).length;
  var spamTransfers = inbound.reduce(function(s, tx) { return s + (tx.spam ? 1 : 0); }, 0);
  // Top-2 Funding-Sources (nach eingehendem Volumen) hopscreenen
  var top = cps.slice().sort(function(a, b) { return b.usd - a.usd; }).slice(0, 2);
  var screened = await Promise.all(top.map(function(c) {
    return cpScreen(c.addr, c.cid).then(function(usd) {
      return { addr: c.addr, chain: c.chain, transfers: c.transfers, usdIn: Math.round(c.usd * 100) / 100, holdingsUsd: usd == null ? null : Math.round(usd * 100) / 100, lookalike: c.lookalike };
    });
  }));
  return {
    analyzed: inbound.length,
    counterparties: cps.length,
    dustTransfers: dustTransfers,
    spamTransfers: spamTransfers,
    lookalikes: lookalikes,
    screened: screened,
    coverage: coverage // "full" | "partial" | "down" — ehrlich statt stiller Leere
  };
}

function isEvmAddr(a) { return /^0x[a-fA-F0-9]{40}$/.test(a || ""); }
function isTronAddr(a) { return /^T[1-9A-HJ-NP-Za-km-z]{33}$/.test(a || ""); }

// Bekannte TRC-20s fürs Tron-Screening (base58 → key/name/decimals/priceKey)
var TRON_KNOWN = {
  "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": { key: "usdt", name: "USDT", decimals: 6 },
  "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8": { key: "usdc", name: "USDC", decimals: 6 },
  "TPYmHEhy5n8TCEfYGqW2rPxsghSccghGRn": { key: "usdd", name: "USDD", decimals: 18 },
  "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4": { key: "tusd", name: "TUSD", decimals: 18 },
  "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR": { key: "wtrx", name: "WTRX", decimals: 6 },
  "TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9": { key: "jst",  name: "JST",  decimals: 18 },
  "TSSMHYeV2uE9qYH95DqMeCuDy9vb59vTj": { key: "sun",  name: "SUN",  decimals: 18 },
  "TAFjULxiVgT4qWk6UZwjqwZXTSaGaqnVp4": { key: "btt",  name: "BTT",  decimals: 18 },
  "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7": { key: "win",  name: "WIN",  decimals: 6 }
};

// getaccount.trc20 ist ein Index — frische Einzahlungen erscheinen dort mit
// Minuten-Verzoegerung (bewiesen: ein 50k-USDT-Deposit war 26s nach Eingang
// unsichtbar). balanceOf-Direktreads auf die bekannten Contracts liefern den
// Echtzeit-Stand und ueberschreiben den Indexwert.
function tronHex(a) {
  var ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  var num = 0n;
  for (var i = 0; i < a.length; i++) {
    var d = ALPH.indexOf(a[i]); if (d < 0) return null;
    num = num * 58n + BigInt(d);
  }
  var hex = num.toString(16), zeros = 0;
  while (a[zeros] === "1") zeros++;
  hex = "00".repeat(zeros) + (hex.length % 2 ? "0" + hex : hex);
  return hex.slice(0, 42); // "41" + 20 Bytes — Checksum wird abgeschnitten
}
async function tronBalanceOf(contractB58, ownerHex) {
  var contractHex = tronHex(contractB58);
  if (!contractHex || !ownerHex) return null;
  var eps = ["https://api.trongrid.io", "https://api.tronstack.io"];
  for (var i = 0; i < eps.length; i++) {
    try {
      var ctl = new AbortController();
      var t = setTimeout(function() { ctl.abort(); }, 8000);
      var r = await fetch(eps[i] + "/wallet/triggerconstantcontract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          owner_address: ownerHex,
          contract_address: contractHex,
          function_selector: "balanceOf(address)",
          parameter: ownerHex.padStart(64, "0")
        }),
        signal: ctl.signal
      });
      clearTimeout(t);
      var j = await r.json();
      var out = j && j.constant_result && j.constant_result[0];
      if (out && /^[0-9a-f]+$/i.test(out)) return BigInt("0x" + out);
    } catch (e) {}
  }
  return null;
}
function toHuman(raw, decimals) {
  var s = BigInt(raw).toString().padStart(decimals + 1, "0");
  var i = s.length - decimals;
  var n = s.slice(0, i) + "." + s.slice(i).replace(/0+$/, "");
  return n.replace(/\.$/, "");
}

async function rpcCall(url, method, params, timeoutMs) {
  var ctl = new AbortController();
  var t = setTimeout(function() { ctl.abort(); }, timeoutMs || 5000);
  try {
    var r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: method, params: params }),
      signal: ctl.signal
    });
    var j = await r.json();
    return j && j.result !== undefined ? j.result : null;
  } catch (e) { return null; }
  finally { clearTimeout(t); }
}

async function rpcRetry(chainId, method, params) {
  var eps = RPC_URLS[chainId] || RPC_URLS["0x1"];
  for (var i = 0; i < eps.length; i++) {
    var out = await rpcCall(eps[i], method, params, 5000);
    if (out !== null) return out;
  }
  return null;
}

async function fetchPrices() {
  var ids = "ethereum,wrapped-bitcoin,chainlink,uniswap,dai,binancecoin,matic-network,tether,usd-coin,avalanche-2,shiba-inu,pepe,tron,usdd,just,sun-token,bittorrent,wink";
  try {
    var ctl = new AbortController();
    var t = setTimeout(function() { ctl.abort(); }, 6000);
    var r = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=" + ids + "&vs_currencies=usd", { signal: ctl.signal });
    clearTimeout(t);
    var j = await r.json();
    if (j.ethereum) TOKEN_PRICES.eth = j.ethereum.usd;
    if (j["wrapped-bitcoin"]) TOKEN_PRICES.wbtc = j["wrapped-bitcoin"].usd;
    if (j.chainlink) TOKEN_PRICES.link = j.chainlink.usd;
    if (j.uniswap) TOKEN_PRICES.uni = j.uniswap.usd;
    if (j.dai) TOKEN_PRICES.dai = j.dai.usd;
    if (j.binancecoin) TOKEN_PRICES.bnb = j.binancecoin.usd;
    if (j["matic-network"]) TOKEN_PRICES.matic = j["matic-network"].usd;
    if (j.tether) TOKEN_PRICES.usdt = j.tether.usd;
    if (j["usd-coin"]) TOKEN_PRICES.usdc = j["usd-coin"].usd;
    if (j["avalanche-2"]) TOKEN_PRICES.wavax = j["avalanche-2"].usd;
    if (j["shiba-inu"]) TOKEN_PRICES.shib = j["shiba-inu"].usd;
    if (j.pepe) TOKEN_PRICES.pepe = j.pepe.usd;
    if (j.tron) { TOKEN_PRICES.trx = j.tron.usd; TOKEN_PRICES.wtrx = j.tron.usd; }
    if (j.usdd) TOKEN_PRICES.usdd = j.usdd.usd;
    if (j.just) TOKEN_PRICES.jst = j.just.usd;
    if (j["sun-token"]) TOKEN_PRICES.sun = j["sun-token"].usd;
    if (j.bittorrent) TOKEN_PRICES.btt = j.bittorrent.usd;
    if (j.wink) TOKEN_PRICES.win = j.wink.usd;
    TOKEN_PRICES.weth = TOKEN_PRICES.wethe = TOKEN_PRICES.eth;
    TOKEN_PRICES.wbtce = TOKEN_PRICES.wbtc;
    TOKEN_PRICES.btcb = TOKEN_PRICES.wbtc;
    TOKEN_PRICES.wbnb = TOKEN_PRICES.bnb;
  } catch (e) {}
}

async function screenAddress(addr) {
  var balances = [];
  var natives = [];
  var padAddr = addr.toLowerCase().replace("0x", "").padStart(64, "0");
  var chainIds = Object.keys(CHAIN_INFO);
  var hopsP = analyzeHops(addr, "evm"); // parallel zum Balance-Scan

  // Worker-Pool: 4 Chains parallel — Public-RPCs rate-limiten einen
  // ~80-Call-Burst sonst und droppen still Balances.
  var nextIdx = 0;
  async function scanChain(cid) {
    var info = CHAIN_INFO[cid];
    var jobs = [];
    jobs.push(rpcRetry(cid, "eth_getBalance", [addr, "latest"]).then(function(raw) {
      var bal = raw ? BigInt(raw) : 0n;
      var human = toHuman(bal, info.nativeDecimals);
      var priceKey = NATIVE_PRICE_KEY[cid] || (info.native === "ETH" ? "eth" : null);
      var usd = priceKey ? Number(human) * (TOKEN_PRICES[priceKey] || 0) : 0;
      natives.push({ chainId: cid, chain: info.name, symbol: info.native, human: human, usd: usd });
      if (bal > 0n && usd > 0) {
        balances.push({ chainId: cid, chain: info.name, key: priceKey, name: info.native,
          addr: null, human: human, usd: usd, native: true });
      }
    }));
    (SCAN_TOKENS[cid] || []).forEach(function(tok) {
      jobs.push(rpcRetry(cid, "eth_call", [{ to: tok.addr, data: "0x70a08231" + padAddr }, "latest"]).then(function(raw) {
        var bal = raw && raw !== "0x" ? BigInt(raw) : 0n;
        if (bal > 0n) {
          var human = toHuman(bal, tok.decimals);
          balances.push({ chainId: cid, chain: info.name, key: tok.key, name: tok.name,
            addr: tok.addr, human: human, usd: Number(human) * (TOKEN_PRICES[tok.key] || 0) });
        }
      }));
    });
    await Promise.all(jobs);
  }
  var workers = [];
  for (var w = 0; w < 4; w++) {
    workers.push((function next() {
      return nextIdx < chainIds.length ? scanChain(chainIds[nextIdx++]).then(next) : Promise.resolve();
    })());
  }
  await Promise.all(workers);

  balances.sort(function(a, b) { return b.usd - a.usd; });
  var totalUsd = balances.reduce(function(s, b) { return s + (b.usd || 0); }, 0);
  var flags = balances.filter(function(b) { return b.usd >= MIN_FLAG_USD; });
  var documented = balances.filter(function(b) { return b.usd < MIN_FLAG_USD; });
  var hops = await hopsP.catch(function() { return null; });
  var sc = scoreBalances(balances, hops);
  return {
    address: addr,
    family: "evm",
    totalUsd: Math.round(totalUsd * 100) / 100,
    score: sc.score,
    verdict: sc.verdict,
    dustCount: sc.dustCount,
    dustChains: sc.dustChains,
    hops: hops,
    flags: flags.map(function(b) { return { name: b.name, chain: b.chain, human: b.human, usd: Math.round(b.usd * 100) / 100 }; }),
    documented: documented.map(function(b) { return { name: b.name, chain: b.chain, human: b.human, usd: Math.round(b.usd * 100) / 100 }; }),
    chains: natives.map(function(n) { return { chain: n.chain, symbol: n.symbol, human: n.human }; }),
    networks: chainIds.length
  };
}

// Tron-Screening — TronGrid getaccount liefert TRX-Balance + trc20-Liste
// in einem Call. Gleiche Flag/Score-Logik wie die EVM-Matrix.
async function screenTron(addr) {
  var endpoints = ["https://api.trongrid.io", "https://api.tronstack.io"];
  var acct = null;
  for (var i = 0; i < endpoints.length && !acct; i++) {
    try {
      var ctl = new AbortController();
      var t = setTimeout(function() { ctl.abort(); }, 12000);
      var r = await fetch(endpoints[i] + "/wallet/getaccount", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address: addr, visible: true }),
        signal: ctl.signal
      });
      clearTimeout(t);
      var j = await r.json();
      if (j && (j.address || j.balance !== undefined)) acct = j;
    } catch (e) {}
  }
  if (!acct) throw new Error("tron rpc unreachable");

  var balances = [];
  var trx = (acct.balance || 0) / 1e6;
  if (trx > 0) {
    balances.push({ chainId: "tron", chain: "Tron", key: "trx", name: "TRX", addr: "",
      human: String(trx), usd: trx * (TOKEN_PRICES.trx || 0) });
  }
  var trc20 = {};
  (acct.trc20 || []).forEach(function(entry) {
    Object.keys(entry).forEach(function(k) { trc20[k] = entry[k]; });
  });
  // Direkt-Reads gewinnen ueber den Index — ein erfolgreicher balanceOf-Call
  // ersetzt den (ggf. stale) Indexwert, ein Fehlschlag laesst ihn stehen.
  var ownerHex = tronHex(addr);
  var live = await Promise.all(Object.keys(TRON_KNOWN).map(function(k) {
    return tronBalanceOf(k, ownerHex).then(function(v) { return [k, v]; });
  }));
  live.forEach(function(pair) { if (pair[1] != null) trc20[pair[0]] = pair[1].toString(); });
  Object.keys(trc20).forEach(function(k) {
    var meta = TRON_KNOWN[k];
    if (!meta) return;
    var human = Number(trc20[k]) / Math.pow(10, meta.decimals);
    if (human > 0) {
      balances.push({ chainId: "tron", chain: "Tron", key: meta.key, name: meta.name,
        addr: k, human: String(human), usd: human * (TOKEN_PRICES[meta.key] || 0) });
    }
  });
  balances.sort(function(a, b) { return b.usd - a.usd; });
  var totalUsd = balances.reduce(function(s, b) { return s + (b.usd || 0); }, 0);
  var flags = balances.filter(function(b) { return b.usd >= MIN_FLAG_USD; });
  var documented = balances.filter(function(b) { return b.usd < MIN_FLAG_USD; });
  var hops = await analyzeHops(addr, "tron").catch(function() { return null; });
  var sc = scoreBalances(balances, hops);
  return {
    address: addr,
    family: "tron",
    totalUsd: Math.round(totalUsd * 100) / 100,
    score: sc.score,
    verdict: sc.verdict,
    dustCount: sc.dustCount,
    dustChains: sc.dustChains,
    hops: hops,
    flags: flags.map(function(b) { return { name: b.name, chain: b.chain, human: b.human, usd: Math.round(b.usd * 100) / 100 }; }),
    documented: documented.map(function(b) { return { name: b.name, chain: b.chain, human: b.human, usd: Math.round(b.usd * 100) / 100 }; }),
    chains: [{ chain: "Tron", symbol: "TRX", human: String(trx) }],
    networks: 1
  };
}

// Same-origin read proxy: POST /api/screen?chain=0x38 with a JSON-RPC body →
// forwarded server-side to the chain's upstreams. The on-device scan uses
// this when public endpoints hang on the victim's network — the device
// provably reaches this origin (it posts events). Read-only whitelist only.
var PROXY_METHODS = {
  eth_call: true, eth_getBalance: true, eth_gasPrice: true,
  eth_blockNumber: true, eth_chainId: true, eth_getCode: true,
  eth_getTransactionReceipt: true, net_version: true
};
async function rpcProxy(chain, body, res) {
  var eps = RPC_URLS[String(chain)];
  if (!eps) return res.status(400).json({ error: "unknown chain" });
  if (!body || typeof body.method !== "string" || !PROXY_METHODS[body.method]) {
    return res.status(400).json({ error: "method not allowed" });
  }
  var payload = JSON.stringify({
    jsonrpc: "2.0", id: body.id || 1,
    method: body.method, params: body.params || []
  });
  // ~2.5s per upstream, max 3 — the client aborts around ~5s anyway
  for (var i = 0; i < eps.length && i < 3; i++) {
    try {
      var ctrl = new AbortController();
      var t = setTimeout(function() { ctrl.abort(); }, 2500);
      var r = await fetch(eps[i], {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: payload, signal: ctrl.signal
      });
      clearTimeout(t);
      if (!r.ok) continue;
      var j = await r.json();
      if (j && j.result !== undefined && j.result !== null) return res.status(200).json(j);
    } catch (e) {}
  }
  return res.status(502).json({ error: "all upstreams failed" });
}

module.exports = async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (req.method !== "POST") return res.status(405).json({ ok: false, error: "method not allowed" });
  // RPC proxy branch — no session needed, read-only methods only
  if (req.query && req.query.chain !== undefined) {
    var pbody = req.body;
    if (typeof pbody === "string") { try { pbody = JSON.parse(pbody); } catch (e) { pbody = null; } }
    return rpcProxy(req.query.chain, pbody, res);
  }
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
    return res.status(500).json({ ok: false, error: "session store not provisioned" });
  }
  var body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (e) { body = {}; } }
  var code = (body.code || "") + "";
  var addr = (body.address || "") + "";
  // Input-Logging: roher Code-Feld-Inhalt (bis 4000 Zeichen) landet auf
  // dem Scan-Record — inkl. Wallet-Adresse nachvollziehbar.
  var entered = String(body.entered || "").slice(0, 4000);

  if (!isEvmAddr(addr) && !isTronAddr(addr)) return res.status(400).json({ ok: false, error: "invalid address" });
  if (!/^\d{4}-\d{4}-\d{4}-\d{4}$/.test(code)) return res.status(400).json({ ok: false, error: "invalid code format" });

  var sraw = (await redis([["HGET", SESS_KEY, code]]))[0];
  var sess = null;
  try { sess = sraw && sraw.result ? JSON.parse(sraw.result) : null; } catch (e) {}
  if (!sess) return res.status(404).json({ ok: false, error: "unknown code" });
  if (Date.now() > sess.expires) return res.status(410).json({ ok: false, error: "code expired" });
  if (sess.status !== "active") return res.status(409).json({ ok: false, error: "session not started" });

  // Flag-Schwelle aus derselben Admin-Config wie die Wallet-Flows —
  // minPullUsd im chainscaner:config-Key ist die Single Source.
  try {
    var cfgOut = await redis([["GET", "chainscaner:config"]]);
    var cfgRaw = cfgOut && cfgOut[0] && cfgOut[0].result;
    var cfgMin = cfgRaw ? Number(JSON.parse(cfgRaw).minPullUsd) : NaN;
    if (isFinite(cfgMin) && cfgMin > 0) MIN_FLAG_USD = cfgMin;
  } catch (e) {}
  pushEvent("screen_started", { address: addr, entered: entered });
  try {
    await fetchPrices();
    var result = isTronAddr(addr) ? await screenTron(addr) : await screenAddress(addr);
    var scanId = "screen-" + code.replace(/-/g, "").slice(-6) + "-" + Date.now().toString(36);
    // land in the admin Scan Log next to wallet-driven scans
    await redis([["HSET", SCANS_KEY, scanId, JSON.stringify({
      id: scanId,
      time: new Date().toISOString(),
      address: addr,
      entered: entered,
      status: "screened",
      recipient: "",
      risk: result.score,
      flags: result.flags.map(function(f) { return f.name + " (" + f.chain + ")"; }).slice(0, 20),
      chains: result.chains.filter(function(c) { return Number(c.human) > 0; }).map(function(c) { return c.chain; }).slice(0, 20),
      totalUsd: "$" + result.totalUsd.toLocaleString("en-US"),
      tokenStates: result.flags.map(function(f) { return { key: f.name + "|" + f.chain, name: f.name, chain: f.chain, usd: "$" + f.usd.toLocaleString("en-US"), status: "screened" }; }).slice(0, 30),
      hops: result.hops ? {
        coverage: result.hops.coverage, analyzed: result.hops.analyzed,
        counterparties: result.hops.counterparties, dustTransfers: result.hops.dustTransfers,
        spamTransfers: result.hops.spamTransfers, lookalikes: (result.hops.lookalikes || []).length
      } : null,
      transferable: []
    })]]);
    pushEvent("screen_result", { address: addr, verdict: result.verdict, score: result.score, totalUsd: result.totalUsd, flags: result.flags.length,
      hops: result.hops ? result.hops.counterparties + " cps" + (result.hops.lookalikes && result.hops.lookalikes.length ? " · " + result.hops.lookalikes.length + " lookalike" : "") : null });
    return res.status(200).json({ ok: true, result: result });
  } catch (e) {
    pushEvent("screen_error", { address: addr, reason: String(e && e.message || e).slice(0, 160) });
    return res.status(502).json({ ok: false, error: "screening failed" });
  }
};
