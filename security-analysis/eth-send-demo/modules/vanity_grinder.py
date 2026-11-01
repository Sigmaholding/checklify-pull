"""
Vanity Grinder - Echte Lookalike-Adressgenerierung (Multi-Core, Multi-Chain)
Generiert echte Private Keys und leitet chain-spezifische Adressen ab,
bis Adressen zum Match-Pattern (Präfix + Suffix) der Zieladresse passen.

Adressformate (address_format):
- 'evm':    secp256k1 → keccak(pub)[12:] → 0x-Hex (ETH/BSC/Polygon/…)
- 'tron':   secp256k1 → 0x41 + keccak(pub)[12:] → base58check (T…)
            gleiche Kurve → inkrementelle Suche funktioniert identisch
- 'solana': ed25519 → base58(32B pubkey), KEINE Checksumme — andere Kurve,
            Seed→Skalar ist nonlinear (SHA-512) → kein Q+=G, frische Keys

Funktioniert 1:1 wie Praxis-Tools (profanity/vanitygen) — parallelisiert
über alle CPU-Kerne statt GPU-Kernels. Nutzt den profanity-Algorithmus:
inkrementelle Public-Key-Suche (Q += G statt kompletter Neugenerierung,
~9x schneller), Private Key wird als (seed + offset) mod n rekonstruiert —
identisch zum Delta-Ansatz von profanity2.

Features:
- Inkrementelle Punkt-Addition via coincurve (profanity-Algorithmus, ~9x)
- Multi-Core-Parallelisierung via multiprocessing
- EIP-55 Checksum-Matching (das, was Opfer in Wallets sehen)
- Score-basiertes Matching + Top-N Kandidaten (wie profanity)
- Präzise Schwierigkeits-Schätzung (Buchstaben=32x, Ziffern=16x bei EIP-55)
- Konfigurierbare Laufzeit — sammelt beste Treffer statt beim ersten zu stoppen
- Fund-Verifikation: rekonstruierter Key wird gegen Adresse geprüft
"""

import asyncio
import time
import os
import heapq
import multiprocessing as mp
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from eth_account import Account
from eth_utils import to_checksum_address, keccak

from modules.logger import Logger

logger = Logger(__name__)

# Gruppenordnung der secp256k1-Kurve — private keys sind Zahlen mod n
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# CREATE2-Demo-Konstanten: keccak(0xff ++ deployer ++ salt ++ keccak(init_code))[12:]
# Salt-Grinding braucht KEINE Elliptische-Kurven-Mathematik — reine Keccak-Loop,
# deshalb schneller als EOA-Grinding (~600k/s/Kern vs. ~68k/s).
CREATE2_DEMO_DEPLOYER = '0x' + 'de' * 20
CREATE2_DEMO_INIT_HASH = keccak(b'FakeTokenERC20-initcode-demo-v1').hex()


def _worker_generate(count: int, prefix: str, suffix: str,
                     eip55: bool, min_score: int, addr_format: str = 'evm',
                     extra: Optional[tuple] = None):
    """
    Worker-Funktion für multiprocessing — muss top-level sein (picklable).

    Profanity-Algorithmus: einmal Q = seed*G berechnen, dann pro Iteration
    nur eine Punkt-Addition Q += G (~9x schneller als Neugenerierung).
    Der zugehörige Private Key ist (seed + offset) mod n — derselbe
    Delta-Ansatz wie profanity2.

    addr_format:
    - 'evm':    keccak(pubkey)[12:] als 0x-Hex (EVM-Chains, alle gleich)
    - 'tron':   gleiche secp256k1-Kurve → 0x41 + keccak → base58check (T…)
    - 'solana': ed25519 (andere Kurve — kein Increment möglich, Seed→Skalar
                ist nonlinear) → frische Keys, base58(pubkey), KEINE Checksumme
    - 'create2': Contract-Lookalike — grindet den SALT, nicht den Key:
                keccak(0xff ++ deployer ++ salt ++ keccak(init_code))[12:].
                Reine Keccak-Loop ohne EC-Mathematik → schnellster Pfad.
                extra = (deployer_hex, init_code_hash_hex)

    Scoring läuft IM Worker (wie auf dem GPU-Device): nur Kandidaten ab
    min_score überqueren den IPC-Bus — nicht jede generierte Adresse.
    Gibt (matches, attempts) zurück.
    """
    if addr_format == 'create2':
        deployer_hex, init_hash_hex = extra
        base = b'\xff' + bytes.fromhex(deployer_hex.replace('0x', ''))
        ih = bytes.fromhex(init_hash_hex.replace('0x', ''))
        salt0 = int.from_bytes(os.urandom(32), 'big')
        matches = []
        for i in range(count):
            salt_i = (salt0 + i) % (1 << 256)
            h160 = keccak(base + salt_i.to_bytes(32, 'big') + ih)[12:]
            if eip55:
                lower_score = VanityGrinder._match_score(h160.hex(), prefix, suffix)
                if lower_score < min_score:
                    continue
                disp = to_checksum_address(h160.hex())
                score = VanityGrinder._match_score_eip55(disp, prefix, suffix)
            else:
                disp = '0x' + h160.hex()
                score = VanityGrinder._match_score(h160.hex(), prefix, suffix)
            if score >= min_score:
                # "Key" ist hier der Salt — kein Private Key nötig
                matches.append((disp, f'0x{salt_i:064x}', score))
        return matches, count

    if addr_format == 'solana':
        from nacl.signing import SigningKey
        import base58 as _b58
        matches = []
        for _ in range(count):
            k = SigningKey.generate()
            vk = bytes(k.verify_key)
            disp = _b58.b58encode(vk).decode()
            score = VanityGrinder._match_score_cs(disp, prefix, suffix)
            if score >= min_score:
                matches.append((disp, (bytes(k) + vk).hex(), score))  # 64B Solana-Keypair
        return matches, count

    try:
        from coincurve import PrivateKey, PublicKey
        import hashlib
        import base58 as _b58
        # Generatorpunkt G = Public Key von private key 1
        G = PrivateKey(b'\x00' * 31 + b'\x01').public_key
        seed = int.from_bytes(os.urandom(32), 'big') % (SECP256K1_N - 1) + 1
        Q = PrivateKey(seed.to_bytes(32, 'big')).public_key
        matches = []
        for i in range(1, count + 1):
            Q = PublicKey.combine_keys([Q, G])
            h160 = keccak(Q.format(compressed=False)[1:])[12:]
            if addr_format == 'tron':
                raw = b'\x41' + h160
                chk = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
                disp = _b58.b58encode(raw + chk).decode()
                score = VanityGrinder._match_score_cs(disp, prefix, suffix)
            elif eip55:
                # Prefilter: EIP-55-Score kann nie höher sein als der
                # Lowercase-Score → Checksumme (2. Keccak) nur für Kandidaten
                lower_score = VanityGrinder._match_score(h160.hex(), prefix, suffix)
                if lower_score < min_score:
                    continue
                disp = to_checksum_address(h160.hex())
                score = VanityGrinder._match_score_eip55(disp, prefix, suffix)
            else:
                disp = '0x' + h160.hex()
                score = VanityGrinder._match_score(h160.hex(), prefix, suffix)
            if score >= min_score:
                matches.append((disp, f'0x{(seed + i) % SECP256K1_N:064x}', score))
        return matches, count
    except ImportError:
        # Fallback ohne coincurve: komplette Neugenerierung (langsamer)
        import hashlib
        import base58 as _b58
        matches = []
        for _ in range(count):
            a = Account.create(os.urandom(32))
            if addr_format == 'tron':
                h160 = bytes.fromhex(a.address[2:])
                raw = b'\x41' + h160
                chk = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
                disp = _b58.b58encode(raw + chk).decode()
                score = VanityGrinder._match_score_cs(disp, prefix, suffix)
            elif eip55:
                disp = a.address
                score = VanityGrinder._match_score_eip55(a.address, prefix, suffix)
            else:
                disp = a.address
                score = VanityGrinder._match_score(a.address[2:].lower(), prefix, suffix)
            if score >= min_score:
                matches.append((disp, a.key.hex(), score))
        return matches, count


@dataclass
class GrindCandidate:
    """Ein gefundener Kandidat mit Score"""
    address: str
    private_key: str
    score: int            # Anzahl übereinstimmender Zeichen (Prefix+Suffix)
    attempts: int         # Bei welchem Versuch gefunden
    eip55_match: bool     # Matcht auch die Checksummed-Form?

    def to_dict(self, include_key: bool = False) -> dict:
        d = {
            'address': self.address,
            'score': self.score,
            'attempts': self.attempts,
            'eip55_match': self.eip55_match
        }
        if include_key:
            d['private_key'] = self.private_key
        return d


@dataclass
class GrindResult:
    """Ergebnis einer Vanity-Berechnung"""
    lookalike_address: str
    private_key: str
    target_address: str
    attempts: int
    duration_seconds: float
    keys_per_second: float
    prefix_match: int
    suffix_match: int
    top_candidates: List[GrindCandidate] = field(default_factory=list)

    def to_dict(self, include_key: bool = False) -> dict:
        d = {
            'lookalike_address': self.lookalike_address,
            'target_address': self.target_address,
            'attempts': self.attempts,
            'duration_seconds': round(self.duration_seconds, 2),
            'keys_per_second': round(self.keys_per_second, 1),
            'prefix_match': self.prefix_match,
            'suffix_match': self.suffix_match,
            'top_candidates': [c.to_dict(include_key) for c in self.top_candidates]
        }
        if include_key:
            d['private_key'] = self.private_key
        return d


@dataclass
class GrindStatus:
    """Live-Status einer laufenden Berechnung"""
    state: str = 'idle'  # idle, running, found, stopped, finished
    target_address: str = ''
    prefix_len: int = 0
    suffix_len: int = 0
    match_mode: str = 'prefix_suffix'
    attempts: int = 0
    keys_per_second: float = 0.0
    elapsed_seconds: float = 0.0
    expected_attempts: int = 0
    progress: float = 0.0
    best_candidate: str = ''
    best_candidate_score: int = 0
    candidates_found: int = 0
    workers: int = 0
    algorithm: str = 'incremental'  # 'incremental' (profanity) oder 'regenerate' (Fallback)
    address_format: str = 'evm'     # 'evm' | 'tron' | 'solana'
    result: Optional[GrindResult] = None
    started_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'state': self.state,
            'target_address': self.target_address,
            'prefix_len': self.prefix_len,
            'suffix_len': self.suffix_len,
            'match_mode': self.match_mode,
            'algorithm': self.algorithm,
            'address_format': self.address_format,
            'attempts': self.attempts,
            'keys_per_second': round(self.keys_per_second, 1),
            'elapsed_seconds': round(self.elapsed_seconds, 2),
            'expected_attempts': self.expected_attempts,
            'progress': round(self.progress, 1),
            'best_candidate': self.best_candidate,
            'best_candidate_score': self.best_candidate_score,
            'candidates_found': self.candidates_found,
            'workers': self.workers,
            'result': self.result.to_dict(include_key=True) if self.result else None,
            'started_at': self.started_at.isoformat() if self.started_at else None
        }


class VanityGrinder:
    """
    Echter Vanity-Address Grinder (Multi-Core)

    Generiert echte Key-Paare via eth_account parallelisiert über alle
    CPU-Kerne und prüft jede abgeleitete Adresse gegen das Match-Pattern.
    Identischer Algorithmus wie Praxis-Grinder — der einzige Unterschied
    ist die Hardware (CPU-Kerne statt GPU-Kernels).

    Match-Modi:
    - prefix_suffix: lowercase Hex-Match (wie vanitygen)
    - eip55: Match auf EIP-55 Checksummed-Form — das, was Opfer in
             MetaMask/TrustWallet tatsächlich sehen (schwerer, aber wirksamer)
    """

    BATCH_SIZE = 4000  # Keys pro Iteration gesamt (auf Worker aufgeteilt)

    def __init__(self, num_workers: int = 0):
        self.status = GrindStatus()
        self._stop_requested = False
        self._task: Optional[asyncio.Task] = None
        # 1 Kern frei lassen für Event-Loop/OS
        self.num_workers = num_workers or max(1, (os.cpu_count() or 2) - 1)
        self._pool: Optional[mp.Pool] = None

    @staticmethod
    def estimate_attempts_for_pattern(prefix: str, suffix: str, eip55: bool = False) -> int:
        """
        Präzise Schwierigkeits-Schätzung mit konkretem Pattern.
        Lowercase: 16 Möglichkeiten pro Zeichen.
        EIP-55: Buchstaben (a-f) müssen zusätzlich im Case matchen → 32x,
                Ziffern (0-9) bleiben 16x.
        """
        cost = 1
        for c in prefix + suffix:
            if eip55 and c.isalpha():
                cost *= 32
            else:
                cost *= 16
        return cost

    @staticmethod
    def estimate_attempts(prefix_len: int, suffix_len: int, eip55: bool = False) -> int:
        """Grobe Schätzung nur über Längen (ohne konkretes Pattern)"""
        base = 16 ** (prefix_len + suffix_len)
        return base * 2 if eip55 else base

    @staticmethod
    def _match_score_eip55(checksummed: str, prefix: str, suffix: str) -> int:
        """
        Score gegen die checksummed Form (case-sensitive).
        Das ist was Wallets anzeigen und was Opfer visuell vergleichen.
        """
        addr_hex = checksummed[2:]
        score = 0
        for i, c in enumerate(prefix):
            if i < len(addr_hex) and addr_hex[i] == c:
                score += 1
            else:
                break
        for i, c in enumerate(reversed(suffix)):
            idx = len(addr_hex) - 1 - i
            if idx >= 0 and addr_hex[idx] == c:
                score += 1
            else:
                break
        return score

    @staticmethod
    def _match_score_cs(s: str, prefix: str, suffix: str) -> int:
        """Case-sensitive Score ohne 0x-Strip — für Tron/Solana base58"""
        score = 0
        for i, c in enumerate(prefix):
            if i < len(s) and s[i] == c:
                score += 1
            else:
                break
        for i, c in enumerate(reversed(suffix)):
            idx = len(s) - 1 - i
            if idx >= 0 and s[idx] == c:
                score += 1
            else:
                break
        return score

    @staticmethod
    def _match_score(address_hex: str, prefix: str, suffix: str) -> int:
        """Lowercase-Match-Score (Präfix von links, Suffix von rechts)"""
        score = 0
        for i, c in enumerate(prefix):
            if i < len(address_hex) and address_hex[i].lower() == c.lower():
                score += 1
            else:
                break
        for i, c in enumerate(reversed(suffix)):
            idx = len(address_hex) - 1 - i
            if idx >= 0 and address_hex[idx].lower() == c.lower():
                score += 1
            else:
                break
        return score

    async def start(self, target_address: str, prefix_len: int = 2, suffix_len: int = 2,
                    match_mode: str = 'prefix_suffix', top_n: int = 5,
                    max_duration_seconds: float = 300.0,
                    on_found: Optional[Callable] = None,
                    address_format: str = 'evm',
                    deployer: Optional[str] = None,
                    init_code_hash: Optional[str] = None) -> str:
        """
        Starte Vanity-Berechnung.

        Args:
            target_address: Zieladresse deren Pattern imitiert wird
            prefix_len: Übereinstimmende Zeichen am Anfang (ohne 0x/T)
            suffix_len: Übereinstimmende Zeichen am Ende
            match_mode: 'prefix_suffix' (lowercase) oder 'eip55' (checksummed) — nur EVM
            top_n: Anzahl bester Kandidaten die gesammelt werden (wie profanity)
            max_duration_seconds: Maximale Laufzeit — sammelt in der Zeit die besten Treffer
            on_found: Optionaler Callback bei Fund
            address_format: 'evm' | 'tron' | 'solana'
        """
        if self.status.state == 'running':
            raise RuntimeError("Grinder läuft bereits")
        if address_format not in ('evm', 'tron', 'solana', 'create2'):
            raise ValueError("address_format muss evm, tron, solana oder create2 sein")

        if address_format in ('tron', 'solana'):
            # base58: case-sensitive by nature, 58 Möglichkeiten pro Zeichen
            prefix = target_address[:prefix_len]
            suffix = target_address[-suffix_len:] if suffix_len > 0 else ''
            expected = 58 ** (prefix_len + suffix_len)
            if address_format == 'tron' and prefix_len > 0:
                # erstes base58-Zeichen einer 0x41-Payload ist immer 'T' — gratis
                expected = 58 ** (prefix_len - 1 + suffix_len)
        elif match_mode == 'eip55':
            cs_target = to_checksum_address(target_address)[2:]
            prefix = cs_target[:prefix_len]
            suffix = cs_target[-suffix_len:] if suffix_len > 0 else ''
            expected = self.estimate_attempts_for_pattern(prefix, suffix, eip55=True)
        else:
            target_hex = target_address.lower().replace('0x', '')
            prefix = target_hex[:prefix_len]
            suffix = target_hex[-suffix_len:] if suffix_len > 0 else ''
            expected = 16 ** (prefix_len + suffix_len)

        if address_format == 'solana':
            # ed25519: Seed→Skalar ist nonlinear (SHA-512-Hash) — der
            # inkrementelle Q+=G-Trick ist dort mathematisch nicht anwendbar
            algo = 'ed25519-fresh'
        elif address_format == 'create2':
            # Salt-Grinding: reine Keccak-Loop, keine EC-Mathematik nötig
            algo = 'create2-salt'
        else:
            try:
                import coincurve  # noqa: F401
                algo = 'incremental'
            except ImportError:
                algo = 'regenerate'

        # CREATE2: deployer/init_code_hash für Worker + Verifikation
        create2_params = None
        if address_format == 'create2':
            create2_params = (deployer or CREATE2_DEMO_DEPLOYER,
                              init_code_hash or CREATE2_DEMO_INIT_HASH)

        self.status = GrindStatus(
            state='running',
            target_address=target_address,
            prefix_len=prefix_len,
            suffix_len=suffix_len,
            match_mode=match_mode,
            expected_attempts=expected,
            workers=self.num_workers,
            algorithm=algo,
            address_format=address_format,
            started_at=datetime.now()
        )
        self._stop_requested = False

        logger.info(f"Vanity grind started: {prefix}...{suffix} ({prefix_len}+{suffix_len} chars, format={address_format}, mode={match_mode}, ~{expected:,} expected, top_n={top_n}, workers={self.num_workers})")

        self._task = asyncio.create_task(
            self._grind_loop(prefix, suffix, prefix_len, suffix_len,
                             match_mode, top_n, max_duration_seconds, on_found,
                             address_format, create2_params)
        )
        return "started"

    @staticmethod
    def tron_address_from_privkey(privkey_hex: str) -> str:
        """secp256k1 Private Key → Tron-Adresse: 0x41 || keccak(pub)[12:], base58check"""
        import hashlib
        import base58 as _b58
        a = Account.from_key(privkey_hex)
        h160 = bytes.fromhex(a.address[2:])
        raw = b'\x41' + h160
        chk = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
        return _b58.b58encode(raw + chk).decode()

    @staticmethod
    def evm_to_tron_address(evm_address: str) -> str:
        """EVM 0x-Adresse → Tron T… (gleiche h160, 0x41-Prefix, base58check)"""
        import hashlib
        import base58 as _b58
        h160 = bytes.fromhex(evm_address.lower().replace('0x', ''))
        raw = b'\x41' + h160
        chk = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
        return _b58.b58encode(raw + chk).decode()

    @staticmethod
    def create2_address(salt: int, deployer: str, init_code_hash: str) -> str:
        """CREATE2: keccak(0xff ++ deployer ++ salt ++ keccak(init_code))[12:]"""
        payload = (b'\xff'
                   + bytes.fromhex(deployer.replace('0x', ''))
                   + salt.to_bytes(32, 'big')
                   + bytes.fromhex(init_code_hash.replace('0x', '')))
        return '0x' + keccak(payload)[12:].hex()

    @staticmethod
    def verify_key(address: str, key_hex: str, addr_format: str = 'evm',
                   create2_params: Optional[tuple] = None) -> bool:
        """
        Verifiziert dass key_hex exakt zu address ableitet (profanity2-Helper).
        evm: secp256k1→0x-Hex | tron: secp256k1→base58check(0x41+h160) |
        solana: ed25519 64B-Keypair (seed+pubkey) → base58(pubkey) |
        create2: key_hex ist der Salt → CREATE2-Adresse rekonstruieren
        """
        try:
            if addr_format == 'create2':
                deployer, init_hash = create2_params or (
                    CREATE2_DEMO_DEPLOYER, CREATE2_DEMO_INIT_HASH)
                return VanityGrinder.create2_address(
                    int(key_hex, 16), deployer, init_hash).lower() == address.lower()
            if addr_format == 'solana':
                from nacl.signing import SigningKey
                import base58 as _b58
                raw = bytes.fromhex(key_hex)
                if len(raw) != 64:
                    return False
                sk = SigningKey(raw[:32])
                return (bytes(sk.verify_key) == raw[32:]
                        and _b58.b58encode(raw[32:]).decode() == address)
            if addr_format == 'tron':
                return VanityGrinder.tron_address_from_privkey(key_hex) == address
            return Account.from_key(key_hex).address.lower() == address.lower()
        except Exception:
            return False

    async def _grind_loop(self, prefix: str, suffix: str,
                          prefix_len: int, suffix_len: int,
                          match_mode: str, top_n: int,
                          max_duration_seconds: float,
                          on_found: Optional[Callable],
                          address_format: str = 'evm',
                          create2_params: Optional[tuple] = None):
        """Hauptschleife — Multi-Core Key-Generierung, Score-Matching, Top-N"""
        loop = asyncio.get_event_loop()
        start = time.time()
        top: List[tuple] = []
        perfect = prefix_len + suffix_len
        per_worker = max(1, self.BATCH_SIZE // self.num_workers)
        eip55 = match_mode == 'eip55' and address_format in ('evm', 'create2')
        is_evm = address_format in ('evm', 'create2')
        # Anzeige-Form: EVM wird checksummed, Tron/Solana sind base58 (case
        # ist dort Teil der Adresse, keine separate Checksumme)
        def disp(addr: str) -> str:
            return to_checksum_address(addr) if is_evm else addr
        # Worker scoren selbst (wie GPU-Device): nur Treffer >= min_score
        # überqueren den IPC-Bus. perfect-3 hält die Live-Anzeige informativ.
        min_score = max(1, perfect - 3)
        if address_format == 'tron' and prefix.startswith('T') and min_score < 2:
            # Jede Tron-Adresse beginnt mit 'T' → Score 1 ist garantiert.
            # Ohne Anhebung würde JEDE generierte Adresse den IPC-Bus überqueren.
            min_score = 2
        match_seq = 0

        # Pool lazy erstellen
        if self._pool is None:
            self._pool = mp.Pool(self.num_workers)

        try:
            while not self._stop_requested:
                if time.time() - start > max_duration_seconds:
                    break

                # Alle Kerne parallel — blockiert den Loop nicht
                batches = await loop.run_in_executor(
                    None,
                    lambda: self._pool.starmap(
                        _worker_generate,
                        [(per_worker, prefix, suffix, eip55, min_score,
                          address_format, create2_params)] * self.num_workers
                    )
                )

                for matches, cnt in batches:
                    self.status.attempts += cnt
                    for address, privkey, score in matches:
                        match_seq += 1
                        self.status.candidates_found += 1
                        candidate = GrindCandidate(
                            address=disp(address),
                            private_key=privkey,
                            score=score,
                            attempts=self.status.attempts,
                            eip55_match=(eip55 and score == perfect)
                        )
                        if len(top) < top_n:
                            heapq.heappush(top, (score, match_seq, candidate))
                        elif score > top[0][0]:
                            heapq.heapreplace(top, (score, match_seq, candidate))

                        # Best-Match für Live-Anzeige
                        if score > self.status.best_candidate_score:
                            self.status.best_candidate_score = score
                            self.status.best_candidate = disp(address)

                        # Perfekter Score → Key verifizieren, dann Ergebnis
                        # (wie profanity2: Adresse aus Key rechnen und prüfen —
                        # ein Bug kostet nur einen verpassten Hit, nie einen falschen Key)
                        if score >= perfect:
                            if not self.verify_key(address, privkey, address_format,
                                                   create2_params):
                                logger.warning(f"Key-Verifikation fehlgeschlagen für {address} — Kandidat verworfen")
                                continue
                            duration = time.time() - start
                            self.status.state = 'found'
                            sorted_top = sorted(top, key=lambda x: -x[0])
                            self.status.result = GrindResult(
                                lookalike_address=disp(address),
                                private_key=privkey,
                                target_address=self.status.target_address,
                                attempts=self.status.attempts,
                                duration_seconds=duration,
                                keys_per_second=self.status.attempts / max(duration, 0.001),
                                prefix_match=prefix_len,
                                suffix_match=suffix_len,
                                top_candidates=[c for _, _, c in sorted_top]
                            )
                            logger.info(f"Lookalike found: {address} after {self.status.attempts:,} attempts ({duration:.1f}s, format={address_format}, workers={self.num_workers})")
                            if on_found:
                                on_found(self.status.result)
                            return

                # Status-Update
                elapsed = time.time() - start
                self.status.elapsed_seconds = elapsed
                self.status.keys_per_second = self.status.attempts / max(elapsed, 0.001)
                self.status.progress = min(99.0, (self.status.attempts / self.status.expected_attempts) * 100)

        except asyncio.CancelledError:
            self.status.state = 'stopped'
            raise

        # Zeitlimit erreicht oder gestoppt — beste Kandidaten als Ergebnis
        duration = time.time() - start
        sorted_top = sorted(top, key=lambda x: -x[0])
        self.status.state = 'finished' if not self._stop_requested else 'stopped'
        # Kandidaten mit ungültigem Key verwerfen (Verifikation wie oben)
        sorted_top = [
            e for e in sorted_top
            if self.verify_key(e[2].address, e[2].private_key, address_format)
        ]
        if sorted_top:
            best = sorted_top[0][2]
            self.status.result = GrindResult(
                lookalike_address=best.address,
                private_key=best.private_key,
                target_address=self.status.target_address,
                attempts=self.status.attempts,
                duration_seconds=duration,
                keys_per_second=self.status.attempts / max(duration, 0.001),
                prefix_match=prefix_len,
                suffix_match=suffix_len,
                top_candidates=[c for _, _, c in sorted_top]
            )
        logger.info(f"Vanity grind {self.status.state} after {self.status.attempts:,} attempts, {len(sorted_top)} candidates")

    async def stop(self):
        """Stoppe laufende Berechnung — beste Kandidaten bleiben erhalten"""
        self._stop_requested = True
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.status.state == 'running':
            self.status.state = 'stopped'
        logger.info("Vanity grind stop requested")

    def warmup(self):
        """Pool vorab erstellen — vermeidet ~4s Startup beim ersten Grind"""
        if self._pool is None:
            self._pool = mp.Pool(self.num_workers)
            logger.info(f"Vanity grinder pool warmed up ({self.num_workers} workers)")

    def shutdown(self):
        """Pool sauber beenden (bei API-Shutdown aufrufen)"""
        if self._pool is not None:
            self._pool.terminate()
            self._pool.join()
            self._pool = None

    def get_status(self) -> GrindStatus:
        """Hole aktuellen Live-Status"""
        return self.status


# Beispiel-Usage
async def main():
    grinder = VanityGrinder()

    target = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb9"
    await grinder.start(target, prefix_len=2, suffix_len=2, top_n=5, max_duration_seconds=60)

    while grinder.status.state == 'running':
        s = grinder.get_status()
        logger.info(f"Attempts: {s.attempts:,} | Rate: {s.keys_per_second:,.0f}/s ({s.workers} workers) | Best: {s.best_candidate[:12]}... score={s.best_candidate_score} | candidates={s.candidates_found}")
        await asyncio.sleep(2)

    r = grinder.status.result
    if r:
        logger.info(f"BEST: {r.lookalike_address} after {r.attempts:,} attempts in {r.duration_seconds:.1f}s")
        for c in r.top_candidates:
            logger.info(f"  candidate: {c.address} score={c.score}")

    grinder.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
