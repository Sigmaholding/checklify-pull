"""
Match Advisor - Analysiert Zieladressen und empfiehlt Match-Pattern
Entscheidet automatisch wieviele Zeichen vorne/hinten berechnet werden —
basierend auf Wallet-Anzeige, Kosten-Nutzen und Adress-Eigenschaften.

Das ist der Analyzer-Schritt aus der Praxis: Bevor der Grinder läuft,
entscheidet er wie das Pattern aussehen muss, damit das Opfer die
Adresse für die eigene hält.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from eth_utils import to_checksum_address

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class MatchRecommendation:
    """Empfehlung für Match-Pattern"""
    prefix_len: int
    suffix_len: int
    match_mode: str           # 'prefix_suffix' oder 'eip55'
    difficulty_label: str     # 'Demo', 'Standard', 'Praxis', 'Maximum'
    expected_attempts: int
    est_seconds_cpu: float    # ~5k keys/s
    est_seconds_gpu: float    # ~3.8 GH/s (RTX 4090)
    reasoning: List[str]      # Deutsche Begründungen für die Präsentation
    wallet_display: str       # Wie das Opfer die Adresse im Wallet sieht
    wallet_defense: Optional[Dict] = None   # Aktive Gegenmaßnahme des Wallets

    def to_dict(self) -> dict:
        return {
            'prefix_len': self.prefix_len,
            'suffix_len': self.suffix_len,
            'match_mode': self.match_mode,
            'difficulty_label': self.difficulty_label,
            'expected_attempts': self.expected_attempts,
            'est_seconds_cpu': round(self.est_seconds_cpu, 2),
            'est_seconds_gpu': round(self.est_seconds_gpu, 4),
            'reasoning': self.reasoning,
            'wallet_display': self.wallet_display,
            'wallet_defense': self.wallet_defense
        }


class MatchAdvisor:
    """
    Entscheidet wie das Match-Pattern aussehen muss.

    Praxis-Logik (Chainalysis/USENIX-Studien):
    - Opfer vergleichen nur die im Wallet SICHTBAREN Stellen
    - Wallets kürzen typisch auf 4-6 Zeichen vorne + 4 hinten
    - Mehr Zeichen = teurer (16^ schwieriger pro Zeichen) aber glaubwürdiger
    - EIP-55-Match (mit Großschreibung) ist wirksamer aber ~2x teurer
    """

    # Wallets zeigen Adressen typisch so gekürzt an (sichtbare Zeichen vorn/hinten)
    WALLET_DISPLAYS = {
        'metamask':    (4, 4),   # 0x1234…abcd — Hauptziel realer Angriffe
        'trustwallet': (4, 4),   # 0x1234…abcd
        'coinbase':    (4, 4),   # 0x1234…abcd
        'tronlink':    (5, 5),   # Txxxxx…xxxxx — Tron-Wallet (base58check)
        'phantom':     (4, 4),   # xxxx…xxxx — Solana-Wallet (base58, keine Checksum)
        'explorer':    (8, 9),   # Etherscan zeigt 8+9 Zeichen (CCS'24) — praktisch ungrindbar
        'paranoid':    (5, 5),   # Vorsichtiges Opfer vergleicht mehr Stellen
    }

    # Wallet → Chain/Adressformat (welche Zieladresse das Wallet verarbeitet)
    WALLET_FORMATS = {
        'metamask': 'evm', 'trustwallet': 'evm', 'coinbase': 'evm',
        'explorer': 'evm', 'paranoid': 'evm',
        'tronlink': 'tron', 'phantom': 'solana',
    }

    # Aktive Gegenmaßnahmen — Stand 2026 (Recherche: MetaMask/TrustWallet-Blogs,
    # GitHub PR #42893, Blockaid-Report)
    WALLET_DEFENSES = {
        'metamask': {
            'status': 'active', 'since': '2026',
            'mechanism': 'Blockaid History-Vergleich: eingefügte Adresse wird gegen '
                         'frühere Gegenparteien geprüft — gleiche Enden, andere Mitte '
                         '→ blockierende Warnung + First-Send-Warnung. Alle EVM-Chains.',
            'impact': 'Klassischer 4+4-Angriff auf MetaMask praktisch neutralisiert — '
                      'Angreifer weichen auf undefended Wallets/Chains aus'
        },
        'trustwallet': {
            'status': 'active', 'since': '2026',
            'mechanism': 'Intel Security API: Echtzeit-Check gegen bekannte Scam-/'
                         'Lookalike-DB, Side-by-Side-Vergleich, blockierende Warnung. '
                         '32 EVM-Chains.',
            'impact': 'Wie MetaMask — History-/DB-basierte Erkennung greift'
        },
        'coinbase': {
            'status': 'partial', 'since': '2024',
            'mechanism': 'Spam-Filter für Dust-Transfers in der Activity-Liste',
            'impact': 'Poison-Eintrag landet evtl. nicht sichtbar in der History — '
                      'Angriff verpufft ohne Warnung beim Opfer'
        },
        'tronlink': {
            'status': 'none', 'since': None,
            'mechanism': 'Keine dokumentierte Poisoning-Detection (Stand Recherche)',
            'impact': 'Tron bleibt primäres Ziel — TRC20-USDT + gratis Bandwidth '
                      '+ keine Wallet-Defense = ideale Angriffsfläche'
        },
        'phantom': {
            'status': 'partial', 'since': '2024',
            'mechanism': 'Spam-/NFT-Filter (Blowfish-Simulation für Signatures), '
                         'keine dedizierte History-Vergleichs-Detection',
            'impact': 'Solana bleibt exponiert — keine Checksumme + keine '
                      'Lookalike-Warnung = höchstes strukturelles Risiko'
        },
        'explorer': {
            'status': 'partial', 'since': '2024',
            'mechanism': 'Etherscan flaggt bekannte Poisoning-Adressen + zeigt '
                         '8+9 Zeichen — aber nur wenn das Opfer den Explorer prüft',
            'impact': 'Verteidigt nur die Kette der Prüfung, nicht den Copy-Paste-Flow'
        },
        'paranoid': {
            'status': 'none', 'since': None,
            'mechanism': 'Manuelle Verifikation durch das Opfer',
            'impact': 'Einzige 100%-Verteidigung: vollständige Adresse vergleichen '
                      'oder Adressbuch/ENS nutzen'
        },
    }

    CPU_RATE = 180000    # keys/s auf CPU (coincurve incremental Q+=G, 9 Kerne — gemessen)
    GPU_RATE = 3.8e9     # keys/s auf RTX 4090 (profanity-Benchmark)
    BASE58_RATE = 100000 # keys/s Solana (ed25519 frische Keys — gemessen)

    def recommend(self, target_address: str,
                  victim_balance_usd: float = 0.0,
                  wallet_type: str = 'metamask',
                  budget_seconds: float = 60.0,
                  address_format: Optional[str] = None) -> MatchRecommendation:
        """
        Empfehle Match-Pattern für eine Zieladresse — chain-aware.

        Args:
            target_address: Zieladresse (Opfer)
            victim_balance_usd: Bekanntes Opfer-Vermögen (aus Profiler) — für Kosten-Nutzen
            wallet_type: Welches Wallet das Opfer nutzt → bestimmt sichtbare Zeichen
            budget_seconds: Zeit-Budget für die Berechnung (CPU)
            address_format: 'evm'|'tron'|'solana' — wird aus wallet_type abgeleitet wenn nicht gesetzt
        """
        reasoning: List[str] = []
        if address_format is None:
            address_format = self.WALLET_FORMATS.get(wallet_type, 'evm')
        is_evm = address_format == 'evm'
        # base58-Formate: 58 Symbole/Zeichen, nativ case-sensitive
        alpha = 16 if is_evm else 58
        cpu_rate = {'evm': self.CPU_RATE, 'tron': 300_000,
                    'solana': self.BASE58_RATE}[address_format]

        if is_evm:
            addr_hex = target_address.lower().replace('0x', '')
            cs = to_checksum_address(target_address)[2:]
        else:
            addr_hex = target_address
            cs = target_address

        # 1) Wallet-Anzeige bestimmt benötigte Match-Länge
        disp_p, disp_s = self.WALLET_DISPLAYS.get(wallet_type, (4, 4))
        visible = (f"0x{cs[:disp_p]}…{cs[-disp_s:]}" if is_evm
                   else f"{target_address[:disp_p]}…{target_address[-disp_s:]}")
        reasoning.append(
            f"{wallet_type} zeigt die Adresse als {visible} — das Opfer vergleicht "
            f"nur {disp_p}+{disp_s} Zeichen. Match muss mindestens diese Stellen abdecken."
        )

        # 2) Wallet-Defense-Check (Stand 2026 — MetaMask/TrustWallet haben
        #    History-Vergleich eingebaut: gleiche Enden + andere Mitte → Warnung)
        defense = self.WALLET_DEFENSES.get(wallet_type)
        if defense:
            icon = {'active': '⚠', 'partial': '◐', 'none': '✓'}[defense['status']]
            reasoning.append(
                f"{icon} Wallet-Defense ({defense['status']}, seit {defense['since'] or 'n/a'}): "
                f"{defense['mechanism']} → {defense['impact']}."
            )

        # 3) Adress-Eigenschaften: auffällige Zeichen erhöhen Pattern-Wert
        distinct_prefix = len(set(addr_hex[:6]))
        if distinct_prefix <= 3:
            reasoning.append(
                f"Ziel-Präfix {addr_hex[:6]} hat nur {distinct_prefix} verschiedene Zeichen — "
                f"auffällig und leicht zu imitieren, Match wirkt glaubwürdiger."
            )

        # 4) Kosten-Nutzen: lohnt sich das volle Wallet-Pattern?
        #    Tron: führendes 'T' ist durch 0x41-Byte garantiert → ein Zeichen gratis
        t_free = 1 if (address_format == 'tron' and disp_p > 0) else 0
        full_attempts = alpha ** max(0, disp_p + disp_s - t_free)
        cpu_secs = full_attempts / cpu_rate
        gpu_secs = full_attempts / self.GPU_RATE

        if cpu_secs <= budget_seconds:
            prefix_len, suffix_len = disp_p, disp_s
            label = 'Praxis'
            reasoning.append(
                f"Volles Wallet-Pattern ({disp_p}+{disp_s}) kostet ~{full_attempts:,} Versuche "
                f"({alpha}^n-Alphabet) ≈ {cpu_secs:.0f}s CPU / {gpu_secs:.2f}s GPU — im Budget."
            )
        else:
            # Skaliere runter bis ins Budget passt — Demo-Fall
            for total in range(disp_p + disp_s - 1, 1, -1):
                if alpha ** total / cpu_rate <= budget_seconds:
                    prefix_len = min(5, disp_p, total - 1)
                    suffix_len = min(5, total - prefix_len)
                    label = 'Demo' if total <= 4 else 'Standard'
                    reasoning.append(
                        f"Volles Pattern ({disp_p}+{disp_s}) würde ~{cpu_secs/3600:.1f}h CPU brauchen — "
                        f"reduziert auf {prefix_len}+{suffix_len} für Zeitbudget {budget_seconds:.0f}s. "
                        f"Auf GPU wäre das volle Pattern in {gpu_secs:.1f}s fertig — genau deshalb "
                        f"nutzen echte Angreifer GPU-Farmen."
                    )
                    break
            else:
                prefix_len, suffix_len, label = 2, 2, 'Demo'

        # 5) Match-Modus
        if is_evm:
            eip55_attempts = (alpha ** (prefix_len + suffix_len)) * 2
            match_mode = 'eip55' if eip55_attempts / cpu_rate <= budget_seconds * 2 else 'prefix_suffix'
            if match_mode == 'eip55':
                reasoning.append(
                    "EIP-55-Modus: Matcht auch die Groß-/Kleinschreibung — das ist exakt was das Opfer "
                    "im Wallet sieht. Wirksamste Form, ~2x teurer pro Buchstaben-Position."
                )
            else:
                reasoning.append(
                    "Lowercase-Modus: Matcht nur die Hex-Zeichen — ausreichend wenn das Opfer "
                    "adressen lowercase vergleicht oder die Wallet-Kürzel-Form."
                )
        else:
            match_mode = 'prefix_suffix'
            if address_format == 'solana':
                reasoning.append(
                    "Solana: base58 ist nativ case-sensitive UND hat keine Checksumme — "
                    "jedes Zeichen trägt den vollen visuellen Match, ein Vertipper schlägt "
                    "nicht auf. Strukturell gefährlichste Chain fürs Kopieren."
                )
            else:
                reasoning.append(
                    "Tron: base58check ist nativ case-sensitive — Checksumme (sha256d) sitzt "
                    "in den letzten 4 Bytes, schwächt Suffix-Matching nicht ab."
                )

        # 6) Vermögens-Check (Kosten-Nutzen)
        if victim_balance_usd > 0:
            gas_cost = 0.0 if address_format == 'tron' else 2.0
            if victim_balance_usd > 100:
                reasoning.append(
                    f"Opfer-Vermögen ${victim_balance_usd:,.0f} >> Angriffskosten ~${gas_cost:.2f} — "
                    f"ROI-Verhältnis extrem, volle Pattern-Stärke gerechtfertigt."
                )
            if victim_balance_usd > 10_000_000 and prefix_len + suffix_len < 9:
                prefix_len = 5
                suffix_len = max(4, suffix_len)
                label = 'Maximum'
                reasoning.append(
                    f"Bei ${victim_balance_usd/1e6:.0f}M Vermögen lohnt sich maximale Stärke: "
                    f"{prefix_len}+{suffix_len} Zeichen — so wurden auch im $68M-Fall (Chainalysis, Mai 2024) "
                    f"mehr Zeichen als das Wallet-Minimum berechnet, damit das Match selbst "
                    f"aufmerksame Opfer täuscht."
                )

        if is_evm:
            expected = self.estimate_pattern(
                (cs[:prefix_len] if match_mode == 'eip55' else addr_hex[:prefix_len]),
                (cs[-suffix_len:] if match_mode == 'eip55' else addr_hex[-suffix_len:]) if suffix_len > 0 else '',
                eip55=(match_mode == 'eip55')
            )
        else:
            eff = prefix_len + suffix_len - (1 if (address_format == 'tron' and prefix_len > 0) else 0)
            expected = alpha ** max(0, eff)

        return MatchRecommendation(
            prefix_len=prefix_len,
            suffix_len=suffix_len,
            match_mode=match_mode,
            difficulty_label=label,
            expected_attempts=expected,
            est_seconds_cpu=expected / cpu_rate,
            est_seconds_gpu=expected / self.GPU_RATE,
            reasoning=reasoning,
            wallet_display=visible,
            wallet_defense=defense
        )

    @staticmethod
    def estimate(prefix_len: int, suffix_len: int, eip55: bool = False) -> int:
        base = 16 ** (prefix_len + suffix_len)
        return base * 2 if eip55 else base

    @staticmethod
    def estimate_pattern(prefix: str, suffix: str, eip55: bool = False) -> int:
        """Präzise Schätzung mit konkretem Pattern — Buchstaben 32x, Ziffern 16x bei EIP-55"""
        cost = 1
        for c in prefix + suffix:
            cost *= 32 if (eip55 and c.isalpha()) else 16
        return cost


# Beispiel-Usage
if __name__ == "__main__":
    advisor = MatchAdvisor()
    rec = advisor.recommend(
        "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb9",
        victim_balance_usd=68_000_000,
        wallet_type='metamask',
        budget_seconds=120
    )
    for r in rec.reasoning:
        logger.info(r)
    logger.info(f"→ Empfehlung: {rec.prefix_len}+{rec.suffix_len} ({rec.match_mode}), ~{rec.expected_attempts:,} Versuche")
