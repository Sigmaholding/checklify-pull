"""
Campaign Economics — Kosten-/ROI-Modell für Address-Poisoning-Kampagnen

Basiert auf gemessenen Real-Daten:
- Bitquery (Ethereum, 12 Monate): $1.86/TX, 45.5M Pairings in 10.3M TXs
  (~4.4 Einträge pro TX, eine TX trug 145) → ~$0.42/Eintrag gebatcht,
  ~6.937 ETH ≈ $19.2M Gas-Gesamtkosten
- USENIX Security 25 (Tsuchiya et al.): ~$1/Eintrag Ethereum, ~$0.01 BSC;
  6.633 Erfolge aus 270M Angriffen → p ≈ 2.46e-5;
  $83.8M Schaden → ~$12.634 Mittelwert pro Erfolg
- CCS'24 Poison-Hunter: $25.5M Gas vs. $144M Schaden → ROI >220%;
  2.900 dedizierte Batching-Contracts gemessen
- Bitquery: ~43s Strom pro Lookalike-Generierung

Beantwortet die Frage: Was kostet eine Kampagne, wann ist der erste
Erfolg statistisch zu erwarten, und lohnt sich das Modell?
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChainProfile:
    """Gas-/Kostenprofil einer Chain für Zero-Value-Poisoning"""
    chain: str
    symbol: str
    native_price_usd: float
    gas_per_entry_single: int      # gas für einen transferFrom-Call
    gas_per_entry_batched: int     # marginale gas pro Eintrag im Batching-Contract
    typical_gwei: float
    note: str = ''
    # Non-EVM Fee-Modell (Solana: fixe Lamports/Signatur, kein gas*gwei)
    fixed_fee_single_usd: Optional[float] = None
    fixed_fee_batched_usd: Optional[float] = None

    @property
    def cost_single_usd(self) -> float:
        if self.fixed_fee_single_usd is not None:
            return self.fixed_fee_single_usd
        return self.gas_per_entry_single * self.typical_gwei * 1e-9 * self.native_price_usd

    @property
    def cost_batched_usd(self) -> float:
        if self.fixed_fee_batched_usd is not None:
            return self.fixed_fee_batched_usd
        return self.gas_per_entry_batched * self.typical_gwei * 1e-9 * self.native_price_usd


# Chain-Profile — gas-Werte aus gemessenen Poisoning-TXs,
# typical_gwei = üblicher Netzwerk-Gaspreis (geht bei ruhigen Phasen niedriger)
CHAINS: Dict[str, ChainProfile] = {
    'ethereum': ChainProfile(
        'ethereum', 'ETH', 3200.0,
        gas_per_entry_single=50_000, gas_per_entry_batched=20_000,
        typical_gwei=5.0,
        note='Ertrag-Chain: nur 6% der Angriffe, aber $79.3M = 95% des Gesamtschadens '
             '(USENIX: 17.4M Transfers → $79.3M). Whale-Targeting, Ø-Opfer-Balance '
             '$338.900. Post-Fusaka: USDT-Poisons +612% wegen billigerem Gas.'
    ),
    'bsc': ChainProfile(
        'bsc', 'BNB', 600.0,
        gas_per_entry_single=50_000, gas_per_entry_batched=15_000,
        typical_gwei=1.0,
        note='Masse-Chain: 252.7M Transfers = 94% aller Angriffe (1.355% häufiger '
             'als ETH), 141M davon zero-value. Nur $4.5M Schaden — Spray-Margin '
             'durch ~1-Cent-Einträge.'
    ),
    'polygon': ChainProfile(
        'polygon', 'POL', 0.40,
        gas_per_entry_single=50_000, gas_per_entry_batched=15_000,
        typical_gwei=50.0,
        note='Sehr billig pro Eintrag — aber kleinere Opfer-Population '
             'und Wallet-Coverage für Token-History schwächer.'
    ),
    'arbitrum': ChainProfile(
        'arbitrum', 'ETH', 3200.0,
        gas_per_entry_single=50_000, gas_per_entry_batched=18_000,
        typical_gwei=0.1,
        note='L2: Sub-Cent-Einträge. transferFrom(0)-Trick funktioniert '
             'bei denselben immutable USDT/USDC-Contracts.'
    ),
    'base': ChainProfile(
        'base', 'ETH', 3200.0,
        gas_per_entry_single=50_000, gas_per_entry_batched=18_000,
        typical_gwei=0.05,
        note='Wie Arbitrum — Coinbase-Wallet-Population wächst, '
             'deswegen zunehmend im Visier realer Kampagnen.'
    ),
    'tron': ChainProfile(
        'tron', 'TRX', 0.15,
        gas_per_entry_single=65_000, gas_per_entry_batched=30_000,
        typical_gwei=0.00042,   # ~420 sun ≈ Energie-Äquivalent
        note='Energy/Bandwidth-Modell: mit gestaktem TRX praktisch gratis '
             '(tägliches Free-Allowance) — deshalb riesige USDT-TRC20-Poisoning-Welle.'
    ),
    'solana': ChainProfile(
        'solana', 'SOL', 150.0,
        gas_per_entry_single=0, gas_per_entry_batched=0, typical_gwei=0.0,
        fixed_fee_single_usd=0.0007,    # 5.000 Lamports/Signatur ~ $0.0007
        fixed_fee_batched_usd=0.0001,   # mehrere SPL-Instructions pro TX
        note='Keine Checksumme in der Adresse — ein falscher Buchstabe sendet '
             'still on-chain statt zu warnen. 5k Lamports/TX, mehrere SPL-'
             'Instructions pro TX batchbar. ed25519 → eigenes Grinder-Format.'
    ),
}


# Alle dokumentierten Gas-/Kosten-Tricks aus der Praxis (USENIX/CCS'24/Bitquery)
GAS_TRICKS = [
    ('batching', 'Batching-Contracts: bis zu 145 Einträge pro TX — Gas amortisiert '
                 'sich auf ~$0.42/Eintrag (Bitquery-Messung, 2.900 Contracts gefunden)'),
    ('zero_value', 'Zero-Value transferFrom: kostet ~$0 Tokenwert — allowance-Check '
                   '0>=0 umgeht Approval komplett, emittiert trotzdem Transfer-Event'),
    ('cheap_chains', 'Billig-Chains: BSC ~1 gwei (1 Cent), Polygon Sub-Cent, '
                     'L2s ~0.5 Cent — gleiche immutable USDT/USDC-Contracts'),
    ('tron_staking', 'Tron: gestaktes TRX = gratis Energy/Bandwidth — '
                     'Einträge faktisch $0, deshalb riesige TRC20-USDT-Welle'),
    ('cross_chain', 'Ein EOA-Lookalike gilt auf ALLEN EVM-Chains gleichzeitig — '
                    'Grinding-Kosten werden über 5+ Chains amortisiert'),
    ('contract_reuse', 'Angriffs-Contracts sind wiederverwendbar — USENIX: '
                       '"can even be recycled from others for free"'),
    ('funding', 'Funding-Addresses: 70 Funder finanzierten 530+ Thief-Wallets — '
                'Gas-Kosten zentralisiert, Thief-Wallets selbst leer'),
    ('gas_timing', 'Gas-Timing: Angriffe in Low-Fee-Fenstern (Nacht/WE UTC) und '
                   'nach Upgrades — Post-Fusaka senkte Gas → USDT-Poisons +612%'),
    ('counterfeit', 'Counterfeit-Token: eigener Contract emitiert identische '
                    'Events — gar kein echtes Token nötig, nur Gas'),
    ('solana_no_checksum', 'Solana: Adresse hat KEINE Checksumme — ein einziges '
                           'falsches Zeichen sendet still on-chain (bei EVM warnt '
                           'EIP-55-Checksum teilweise). Höchste Copy-Risiko-Chain.'),
]


@dataclass
class SuccessModel:
    """Erfolgs-Statistik aus den Messstudien"""
    p_success_per_entry: float = 6633 / 270_000_000   # USENIX: ~1/40.700
    mean_revenue_per_success_usd: float = 83_800_000 / 6633   # ~$12.634 (Whale-skewed)
    median_revenue_per_success_usd: float = 336.0            # Bitquery Median
    source: str = 'USENIX Sec 25 (6.633/270M), Bitquery (Median $336)'


class CampaignEconomics:
    """
    Rechnet Kampagnen-Kosten, Break-even und ROI.

    Kern-Logik: Einträge sind geometrisch verteilt — erwartete Einträge
    bis zum ersten Erfolg = 1/p. Davor verdient man nichts, danach
    amortisiert sich die Kampagne (statistisch).
    """

    GPU_RATE = 3.8e9              # Keys/s RTX 4090 (profanity)
    GPU_COST_PER_HOUR = 1.0       # ~$1/h gemietete GPU (vast.ai-Niveau)
    CPU_POWER_KW = 0.4            # ~400W Rig
    ELECTRICITY_USD_PER_KWH = 0.15

    def __init__(self):
        self.success = SuccessModel()

    def vanity_cost_usd(self, expected_attempts: int, hardware: str = 'gpu') -> float:
        """Kosten der Lookalike-Generierung selbst"""
        if hardware == 'gpu':
            seconds = expected_attempts / self.GPU_RATE
            return seconds / 3600 * self.GPU_COST_PER_HOUR
        seconds = expected_attempts / 180_000   # unsere CPU-Rate
        return seconds / 3600 * self.CPU_POWER_KW * self.ELECTRICITY_USD_PER_KWH

    def entries_to_first_success(self, p: Optional[float] = None) -> float:
        """Geometrische Erwartung: 1/p Einträge bis zum ersten Erfolg"""
        return 1.0 / (p or self.success.p_success_per_entry)

    def evaluate(self, chain: str, entries: int,
                 victim_value_usd: float = 0.0,
                 grind_attempts: int = 0,
                 batched: bool = True,
                 p_success: Optional[float] = None) -> dict:
        """
        Volle Kosten-/ROI-Rechnung einer Kampagne.

        Args:
            chain: Chain-Key aus CHAINS
            entries: Geplante Poisoning-Einträge
            victim_value_usd: Falls gezielt (targeted) — erwarteter Beute-Wert
            grind_attempts: Erwartete Grinder-Versuche (für Vanity-Kosten)
            batched: Batching-Contract (wie Profis) oder Einzel-TXs
            p_success: Überschreibt die Erfolgswahrscheinlichkeit
        """
        prof = CHAINS.get(chain, CHAINS['ethereum'])
        p = p_success or self.success.p_success_per_entry

        cost_per_entry = prof.cost_batched_usd if batched else prof.cost_single_usd
        total_gas = cost_per_entry * entries
        vanity_cost = self.vanity_cost_usd(grind_attempts) if grind_attempts else 0.0
        total_cost = total_gas + vanity_cost

        # Erfolgs-Erwartung über die Kampagne: E[Treffer] = entries * p
        expected_successes = entries * p
        entries_first = self.entries_to_first_success(p)
        cost_first = entries_first * cost_per_entry

        # Erlös: gezielt (victim_value) vs. Spray (Statistik-Mittel)
        revenue_per_success = victim_value_usd if victim_value_usd > 0 else self.success.mean_revenue_per_success_usd
        expected_revenue = expected_successes * revenue_per_success
        ev_per_entry = p * revenue_per_success - cost_per_entry

        return {
            'chain': chain,
            'cost_per_entry_usd': round(cost_per_entry, 4),
            'cost_single_usd': round(prof.cost_single_usd, 4),
            'vanity_cost_usd': round(vanity_cost, 4),
            'total_cost_usd': round(total_cost, 2),
            'entries': entries,
            'p_success_per_entry': p,
            'expected_successes': round(expected_successes, 3),
            'entries_to_first_success': round(entries_first),
            'cost_to_first_success_usd': round(cost_first, 2),
            'expected_revenue_usd': round(expected_revenue, 2),
            'ev_per_entry_usd': round(ev_per_entry, 4),
            'roi_percent': round((expected_revenue - total_cost) / max(total_cost, 0.01) * 100, 1),
            'revenue_mean_usd': round(self.success.mean_revenue_per_success_usd),
            'revenue_median_usd': round(self.success.median_revenue_per_success_usd),
            'chain_note': prof.note,
            'stats_source': self.success.source,
            'batched': batched
        }

    def compare_chains(self, entries: int = 1_000_000,
                       victim_value_usd: float = 0.0,
                       grind_attempts: int = 0) -> List[dict]:
        """Alle Chains im Vergleich — für die Dashboard-Tabelle"""
        return [self.evaluate(c, entries, victim_value_usd, grind_attempts)
                for c in CHAINS]
