"""
Chain Adapter - API-Integration für Simulation
Kommuniziert mit der Intranet-API für Chain-Simulation
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from modules.logger import Logger

logger = Logger(__name__)
from modules.transaction_builder import TransactionData


@dataclass
class BlockData:
    """Block Daten"""
    number: int
    hash: str
    parent_hash: str
    timestamp: datetime
    transactions: List[str]
    gas_used: int
    gas_limit: int
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'number': self.number,
            'hash': self.hash,
            'parent_hash': self.parent_hash,
            'timestamp': self.timestamp.isoformat(),
            'transactions': self.transactions,
            'gas_used': self.gas_used,
            'gas_limit': self.gas_limit
        }


@dataclass
class TransactionData:
    """Transaktionsdaten (erweitert)"""
    hash: str
    from_address: str
    to_address: str
    value: str
    data: str
    block_number: int
    block_hash: str
    gas_used: int
    gas_price: str
    status: str
    timestamp: datetime
    logs: List[dict]
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'hash': self.hash,
            'from': self.from_address,
            'to': self.to_address,
            'value': self.value,
            'data': self.data,
            'block_number': self.block_number,
            'block_hash': self.block_hash,
            'gas_used': self.gas_used,
            'gas_price': self.gas_price,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'logs': self.logs
        }


@dataclass
class LogData:
    """Log Daten"""
    address: str
    topics: List[str]
    data: str
    block_number: int
    block_hash: str
    transaction_hash: str
    log_index: int
    transaction_index: int
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'address': self.address,
            'topics': self.topics,
            'data': self.data,
            'block_number': self.block_number,
            'block_hash': self.block_hash,
            'transaction_hash': self.transaction_hash,
            'log_index': self.log_index,
            'transaction_index': self.transaction_index
        }


class ChainAdapter:
    """
    Chain Adapter für API-Integration
    
    Features:
    - Block retrieval
    - Transaction submission
    - Event query support
    - Balance queries
    - Contract interaction
    """
    
    def __init__(self, api_base_url: str, api_key: Optional[str] = None):
        """
        Initialisiere Chain Adapter
        
        Args:
            api_base_url: Base URL der Intranet-API
            api_key: Optional API Key
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def _get_headers(self) -> Dict[str, str]:
        """HTTP Headers"""
        headers = {
            'Content-Type': 'application/json'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
        
    async def get_latest_block(self) -> Optional[BlockData]:
        """
        Hole den letzten Block
        
        Returns:
            BlockData oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/blocks/latest"
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlockData(
                        number=data['number'],
                        hash=data['hash'],
                        parent_hash=data['parent_hash'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        transactions=data.get('transactions', []),
                        gas_used=data.get('gas_used', 0),
                        gas_limit=data.get('gas_limit', 0)
                    )
                else:
                    logger.info(f"[ChainAdapter] Error getting latest block: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception getting latest block: {e}")
            return None
            
    async def get_block(self, block_number: int) -> Optional[BlockData]:
        """
        Hole einen spezifischen Block
        
        Args:
            block_number: Block Number
            
        Returns:
            BlockData oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/blocks/{block_number}"
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return BlockData(
                        number=data['number'],
                        hash=data['hash'],
                        parent_hash=data['parent_hash'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        transactions=data.get('transactions', []),
                        gas_used=data.get('gas_used', 0),
                        gas_limit=data.get('gas_limit', 0)
                    )
                else:
                    logger.info(f"[ChainAdapter] Error getting block {block_number}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception getting block {block_number}: {e}")
            return None
            
    async def get_transaction(self, tx_hash: str) -> Optional[TransactionData]:
        """
        Hole eine Transaktion
        
        Args:
            tx_hash: Transaction Hash
            
        Returns:
            TransactionData oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/transactions/{tx_hash}"
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return TransactionData(
                        hash=data['hash'],
                        from_address=data['from'],
                        to_address=data['to'],
                        value=data['value'],
                        data=data.get('data', '0x'),
                        block_number=data['block_number'],
                        block_hash=data['block_hash'],
                        gas_used=data['gas_used'],
                        gas_price=data['gas_price'],
                        status=data['status'],
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        logs=data.get('logs', [])
                    )
                else:
                    logger.info(f"[ChainAdapter] Error getting transaction {tx_hash}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception getting transaction {tx_hash}: {e}")
            return None
            
    async def submit_transaction(
        self,
        transaction: TransactionData
    ) -> Optional[str]:
        """
        Reiche eine Transaktion ein
        
        Args:
            transaction: TransactionData
            
        Returns:
            Transaction Hash oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/simulations/transactions"
            
            payload = transaction.to_rpc_format()
            
            async with self.session.post(
                url,
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('transaction_hash')
                else:
                    error_text = await response.text()
                    logger.info(f"[ChainAdapter] Error submitting transaction: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception submitting transaction: {e}")
            return None
            
    async def get_logs(
        self,
        address: Optional[str] = None,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        topics: Optional[List[str]] = None
    ) -> List[LogData]:
        """
        Hole Logs
        
        Args:
            address: Optional Contract Address
            from_block: Optional From Block
            to_block: Optional To Block
            topics: Optional Topics
            
        Returns:
            Liste von LogData
        """
        try:
            url = f"{self.api_base_url}/api/logs"
            
            params = {}
            if address:
                params['address'] = address
            if from_block:
                params['from_block'] = from_block
            if to_block:
                params['to_block'] = to_block
            if topics:
                params['topics'] = topics
                
            async with self.session.get(
                url,
                headers=self._get_headers(),
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logs = data.get('logs', [])
                    
                    return [
                        LogData(
                            address=log['address'],
                            topics=log['topics'],
                            data=log['data'],
                            block_number=log['block_number'],
                            block_hash=log['block_hash'],
                            transaction_hash=log['transaction_hash'],
                            log_index=log['log_index'],
                            transaction_index=log['transaction_index']
                        )
                        for log in logs
                    ]
                else:
                    logger.info(f"[ChainAdapter] Error getting logs: {response.status}")
                    return []
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception getting logs: {e}")
            return []
            
    async def get_balance(
        self,
        address: str,
        token_address: Optional[str] = None
    ) -> Optional[int]:
        """
        Hole Balance einer Adresse
        
        Args:
            address: Die Adresse
            token_address: Optional Token Address (für ERC20)
            
        Returns:
            Balance in Wei oder None bei Fehler
        """
        try:
            if token_address:
                # ERC20 Balance
                url = f"{self.api_base_url}/api/tokens/{token_address}/balance/{address}"
            else:
                # Native Balance
                url = f"{self.api_base_url}/api/balances/{address}"
                
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return int(data['balance'])
                else:
                    logger.info(f"[ChainAdapter] Error getting balance: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception getting balance: {e}")
            return None
            
    async def call_contract(
        self,
        contract_address: str,
        data: str,
        from_address: Optional[str] = None
    ) -> Optional[str]:
        """
        Contract Call (read-only)
        
        Args:
            contract_address: Contract Address
            data: Encoded call data
            from_address: Optional From Address
            
        Returns:
            Result oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/contracts/call"
            
            payload = {
                'to': contract_address,
                'data': data
            }
            
            if from_address:
                payload['from'] = from_address
                
            async with self.session.post(
                url,
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result')
                else:
                    logger.info(f"[ChainAdapter] Error calling contract: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception calling contract: {e}")
            return None
            
    async def estimate_gas(
        self,
        transaction: TransactionData
    ) -> Optional[int]:
        """
        Schätze Gas für eine Transaktion
        
        Args:
            transaction: TransactionData
            
        Returns:
            Gas Limit oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/gas/estimate"
            
            payload = transaction.to_rpc_format()
            
            async with self.session.post(
                url,
                headers=self._get_headers(),
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return int(data['gas_limit'])
                else:
                    logger.info(f"[ChainAdapter] Error estimating gas: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception estimating gas: {e}")
            return None
            
    async def get_gas_price(self) -> Optional[int]:
        """
        Hole aktuellen Gas Price
        
        Returns:
            Gas Price in Wei oder None bei Fehler
        """
        try:
            url = f"{self.api_base_url}/api/gas/price"
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    data = await response.json()
                    return int(data['gas_price'])
                else:
                    logger.info(f"[ChainAdapter] Error getting gas price: {response.status}")
                    return None
                    
        except Exception as e:
            logger.info(f"[ChainAdapter] Exception getting gas price: {e}")
            return None


# Mock Chain Adapter für Testing
class MockChainAdapter:
    """Mock Chain Adapter für Development ohne echte API"""
    
    def __init__(self, api_base_url: str = "http://localhost:3000"):
        self.api_base_url = api_base_url
        self.block_number = 1000000
        self.transactions: Dict[str, dict] = {}
        self.blocks: Dict[int, dict] = {}
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def get_latest_block(self) -> Optional[BlockData]:
        """Mock latest block"""
        return BlockData(
            number=self.block_number,
            hash=f"0x{self.block_number:064x}",
            parent_hash=f"0x{self.block_number-1:064x}",
            timestamp=datetime.now(),
            transactions=[],
            gas_used=1000000,
            gas_limit=15000000
        )
        
    async def get_block(self, block_number: int) -> Optional[BlockData]:
        """Mock get block"""
        return BlockData(
            number=block_number,
            hash=f"0x{block_number:064x}",
            parent_hash=f"0x{block_number-1:064x}",
            timestamp=datetime.now(),
            transactions=[],
            gas_used=1000000,
            gas_limit=15000000
        )
        
    async def get_transaction(self, tx_hash: str) -> Optional[TransactionData]:
        """Mock get transaction"""
        return TransactionData(
            hash=tx_hash,
            from_address="0x1234567890123456789012345678901234567890",
            to_address="0x0987654321098765432109876543210987654321",
            value="0x0",
            data="0x",
            block_number=self.block_number,
            block_hash=f"0x{self.block_number:064x}",
            gas_used=50000,
            gas_price="0x4a817c800",  # 20 GWEI
            status="success",
            timestamp=datetime.now(),
            logs=[]
        )
        
    async def submit_transaction(
        self,
        transaction: TransactionData
    ) -> Optional[str]:
        """Mock submit transaction"""
        tx_hash = f"0x{self.block_number:064x}"
        self.block_number += 1
        return tx_hash
        
    async def get_logs(
        self,
        address: Optional[str] = None,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        topics: Optional[List[str]] = None
    ) -> List[LogData]:
        """Mock get logs"""
        return []
        
    async def get_balance(
        self,
        address: str,
        token_address: Optional[str] = None
    ) -> Optional[int]:
        """Mock get balance"""
        return 1000000000000000000  # 1 ETH
        
    async def call_contract(
        self,
        contract_address: str,
        data: str,
        from_address: Optional[str] = None
    ) -> Optional[str]:
        """Mock call contract"""
        return "0x" + "0" * 64
        
    async def estimate_gas(
        self,
        transaction: TransactionData
    ) -> Optional[int]:
        """Mock estimate gas"""
        return 50000
        
    async def get_gas_price(self) -> Optional[int]:
        """Mock get gas price"""
        return 20000000000  # 20 GWEI


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    # Mock Adapter für Testing
    async with MockChainAdapter() as adapter:
        # Latest Block
        block = await adapter.get_latest_block()
        logger.info(f"Latest block: {block.number}")
        
        # Transaction
        tx = await adapter.get_transaction("0xabc123")
        logger.info(f"Transaction: {tx.hash}")
        
        # Gas Price
        gas_price = await adapter.get_gas_price()
        logger.info(f"Gas price: {gas_price / 1e9} GWEI")
        
        # Balance
        balance = await adapter.get_balance("0x1234567890123456789012345678901234567890")
        logger.info(f"Balance: {balance / 1e18} ETH")


if __name__ == "__main__":
    asyncio.run(main())