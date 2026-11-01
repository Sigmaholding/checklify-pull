"""
Transfer Indexer - Speichert Transfer-Events in PostgreSQL
Mit dedup auf blockHash:logIndex und per-chain partitioning
"""

import asyncio
from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
import asyncpg

from modules.logger import Logger

logger = Logger(__name__)
from modules.types import TransferEvent


@dataclass
class IndexerStats:
    """Indexer Statistiken"""
    total_processed: int = 0
    total_duplicates: int = 0
    total_errors: int = 0
    last_processed_block: int = 0


class TransferIndexer:
    """
    Transfer Indexer für PostgreSQL
    
    Features:
    - Dedup auf blockHash:logIndex
    - Per-chain partitioning
    - Batch inserts für Performance
    - Idempotent processing
    """
    
    def __init__(
        self,
        db_url: str,
        batch_size: int = 100,
        batch_timeout: float = 5.0
    ):
        self.db_url = db_url
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        self.pool: Optional[asyncpg.Pool] = None
        self.batch: List[TransferEvent] = []
        self.stats = IndexerStats()
        self.flush_task: Optional[asyncio.Task] = None
        self.running = False
        
    async def initialize(self):
        """Initialisiere Database Connection und Schema"""
        self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
        
        async with self.pool.acquire() as conn:
            # Schema erstellen
            await self._create_schema(conn)
            
        logger.info("[Indexer] Database initialized")
        
    async def _create_schema(self, conn: asyncpg.Connection):
        """Erstelle Database Schema"""
        # Main table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id BIGSERIAL PRIMARY KEY,
                chain_id INTEGER NOT NULL,
                block_number BIGINT NOT NULL,
                tx_hash TEXT NOT NULL,
                token_address TEXT NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                value NUMERIC NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                log_index INTEGER NOT NULL,
                block_hash TEXT NOT NULL,
                UNIQUE(chain_id, block_hash, log_index)
            )
        """)
        
        # Indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transfers_chain_block 
            ON transfers(chain_id, block_number)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transfers_from_address 
            ON transfers(from_address)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transfers_to_address 
            ON transfers(to_address)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transfers_token_address 
            ON transfers(token_address)
        """)
        
        # Partitioning (PostgreSQL 10+)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transfers_1 
                PARTITION OF transfers FOR VALUES IN (1)
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transfers_56 
                PARTITION OF transfers FOR VALUES IN (56)
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transfers_137 
                PARTITION OF transfers FOR VALUES IN (137)
            """)
        except asyncpg.PostgresError as e:
            logger.info(f"[Indexer] Partitioning not supported or already exists: {e}")
            
    async def start(self):
        """Starte Indexer"""
        self.running = True
        self.flush_task = asyncio.create_task(self._flush_loop())
        logger.info("[Indexer] Started")
        
    async def stop(self):
        """Stoppe Indexer und flush remaining batch"""
        self.running = False
        
        if self.flush_task:
            self.flush_task.cancel()
            
        # Final flush
        await self._flush()
        
        if self.pool:
            await self.pool.close()
            
        logger.info("[Indexer] Stopped")
        
    async def process_event(self, event: TransferEvent):
        """Verarbeite ein Event (add to batch)"""
        self.batch.append(event)
        self.stats.total_processed += 1
        
        # Flush wenn batch size erreicht
        if len(self.batch) >= self.batch_size:
            await self._flush()
            
    async def _flush_loop(self):
        """Periodischer Flush Loop"""
        while self.running:
            try:
                await asyncio.sleep(self.batch_timeout)
                if self.batch:
                    await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.info(f"[Indexer] Flush loop error: {e}")
                
    async def _flush(self):
        """Flush batch to database"""
        if not self.batch:
            return
            
        batch_copy = self.batch.copy()
        self.batch.clear()
        
        try:
            async with self.pool.acquire() as conn:
                # Batch insert mit ON CONFLICT für dedup
                for event in batch_copy:
                    await conn.execute("""
                        INSERT INTO transfers (
                            chain_id, block_number, tx_hash, token_address,
                            from_address, to_address, value, timestamp,
                            log_index, block_hash
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (chain_id, block_hash, log_index) DO NOTHING
                    """,
                        event.chain_id,
                        event.block_number,
                        event.tx_hash,
                        event.token_address,
                        event.from_address,
                        event.to_address,
                        str(event.value),
                        event.timestamp,
                        event.log_index,
                        event.block_hash
                    )
                    
                # Update stats
                result = await conn.fetchval("""
                    SELECT COUNT(*) FROM transfers 
                    WHERE chain_id = $1 AND block_number = $2
                """, batch_copy[0].chain_id, batch_copy[0].block_number)
                
                duplicates = len(batch_copy) - result
                self.stats.total_duplicates += duplicates
                self.stats.last_processed_block = max(
                    e.block_number for e in batch_copy
                )
                
                logger.info(f"[Indexer] Flushed {len(batch_copy)} events ({duplicates} duplicates)")
                
        except Exception as e:
            logger.info(f"[Indexer] Flush error: {e}")
            self.stats.total_errors += len(batch_copy)
            
    async def get_transfers_for_address(
        self,
        address: str,
        chain_id: Optional[int] = None,
        limit: int = 100
    ) -> List[dict]:
        """Hole Transfers für eine Adresse"""
        async with self.pool.acquire() as conn:
            if chain_id:
                query = """
                    SELECT * FROM transfers 
                    WHERE (from_address = $1 OR to_address = $1) 
                    AND chain_id = $2 
                    ORDER BY block_number DESC 
                    LIMIT $3
                """
                rows = await conn.fetch(query, address, chain_id, limit)
            else:
                query = """
                    SELECT * FROM transfers 
                    WHERE (from_address = $1 OR to_address = $1) 
                    ORDER BY block_number DESC 
                    LIMIT $2
                """
                rows = await conn.fetch(query, address, limit)
                
            return [dict(row) for row in rows]
            
    async def get_counterparties(
        self,
        address: str,
        chain_id: Optional[int] = None
    ) -> List[str]:
        """Hole alle Counterparties für eine Adresse"""
        async with self.pool.acquire() as conn:
            if chain_id:
                query = """
                    SELECT DISTINCT 
                        CASE 
                            WHEN from_address = $1 THEN to_address 
                            ELSE from_address 
                        END as counterparty
                    FROM transfers 
                    WHERE (from_address = $1 OR to_address = $1) 
                    AND chain_id = $2
                """
                rows = await conn.fetch(query, address, chain_id)
            else:
                query = """
                    SELECT DISTINCT 
                        CASE 
                            WHEN from_address = $1 THEN to_address 
                            ELSE from_address 
                        END as counterparty
                    FROM transfers 
                    WHERE (from_address = $1 OR to_address = $1)
                """
                rows = await conn.fetch(query, address)
                
            return [row['counterparty'] for row in rows]
            
    async def get_transfer_count(
        self,
        address: str,
        chain_id: Optional[int] = None,
        hours: Optional[int] = None
    ) -> int:
        """Hole Transfer Count für eine Adresse"""
        async with self.pool.acquire() as conn:
            if hours:
                query = """
                    SELECT COUNT(*) FROM transfers 
                    WHERE (from_address = $1 OR to_address = $1)
                    AND timestamp > NOW() - INTERVAL '1 hour' * $2
                """
                if chain_id:
                    query += " AND chain_id = $3"
                    count = await conn.fetchval(query, address, hours, chain_id)
                else:
                    count = await conn.fetchval(query, address, hours)
            else:
                query = """
                    SELECT COUNT(*) FROM transfers 
                    WHERE (from_address = $1 OR to_address = $1)
                """
                if chain_id:
                    query += " AND chain_id = $2"
                    count = await conn.fetchval(query, address, chain_id)
                else:
                    count = await conn.fetchval(query, address)
                    
            return count or 0
            
    def get_stats(self) -> IndexerStats:
        """Hole Indexer Statistiken"""
        return self.stats


# Mock Database für Testing
class MockIndexer:
    """Mock Indexer für Development ohne echte Database"""
    
    def __init__(self):
        self.transfers: List[dict] = []
        self.stats = IndexerStats()
        
    async def initialize(self):
        """Mock initialize"""
        logger.info("[MockIndexer] Initialized")
        
    async def start(self):
        """Mock start"""
        logger.info("[MockIndexer] Started")
        
    async def stop(self):
        """Mock stop"""
        logger.info("[MockIndexer] Stopped")
        
    async def process_event(self, event: TransferEvent):
        """Mock process event"""
        # Dedup check
        event_id = f"{event.block_hash}:{event.log_index}"
        for existing in self.transfers:
            if existing.get('event_id') == event_id:
                self.stats.total_duplicates += 1
                return
                
        self.transfers.append({
            'event_id': event_id,
            'chain_id': event.chain_id,
            'block_number': event.block_number,
            'tx_hash': event.tx_hash,
            'token_address': event.token_address,
            'from_address': event.from_address,
            'to_address': event.to_address,
            'value': event.value,
            'timestamp': event.timestamp,
            'log_index': event.log_index,
            'block_hash': event.block_hash
        })
        
        self.stats.total_processed += 1
        self.stats.last_processed_block = event.block_number
        
    async def get_transfers_for_address(
        self,
        address: str,
        chain_id: Optional[int] = None,
        limit: int = 100
    ) -> List[dict]:
        """Mock get transfers"""
        filtered = [
            t for t in self.transfers 
            if (t['from_address'] == address or t['to_address'] == address)
            and (chain_id is None or t['chain_id'] == chain_id)
        ]
        return sorted(filtered, key=lambda x: x['block_number'], reverse=True)[:limit]
        
    async def get_counterparties(
        self,
        address: str,
        chain_id: Optional[int] = None
    ) -> List[str]:
        """Mock get counterparties"""
        counterparties = set()
        for t in self.transfers:
            if t['from_address'] == address:
                counterparties.add(t['to_address'])
            elif t['to_address'] == address:
                counterparties.add(t['from_address'])
                
        return list(counterparties)
        
    async def get_transfer_count(
        self,
        address: str,
        chain_id: Optional[int] = None,
        hours: Optional[int] = None
    ) -> int:
        """Mock get transfer count"""
        filtered = [
            t for t in self.transfers 
            if (t['from_address'] == address or t['to_address'] == address)
            and (chain_id is None or t['chain_id'] == chain_id)
        ]
        
        if hours:
            # Filter by time (simplified)
            cutoff = datetime.now().timestamp() - (hours * 3600)
            filtered = [
                t for t in filtered 
                if t['timestamp'].timestamp() > cutoff
            ]
            
        return len(filtered)
        
    def get_stats(self) -> IndexerStats:
        """Mock get stats"""
        return self.stats


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    import os
    
    # Database URL aus Environment
    db_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/blockchain")
    
    # Indexer erstellen
    indexer = TransferIndexer(
        db_url=db_url,
        batch_size=100,
        batch_timeout=5.0
    )
    
    # Initialisieren
    await indexer.initialize()
    await indexer.start()
    
    # Beispiel Event
    from modules.types import TransferEvent
    event = TransferEvent(
        chain_id=1,
        block_number=12345678,
        tx_hash="0xabc123",
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        from_address="0x1234567890123456789012345678901234567890",
        to_address="0x0987654321098765432109876543210987654321",
        value=1000000,
        timestamp=datetime.now(),
        log_index=0,
        block_hash="0xdef456"
    )
    
    # Event verarbeiten
    await indexer.process_event(event)
    
    # Stats
    stats = indexer.get_stats()
    logger.info(f"Processed: {stats.total_processed}, Duplicates: {stats.total_duplicates}")
    
    # Stoppen
    await indexer.stop()


if __name__ == "__main__":
    asyncio.run(main())