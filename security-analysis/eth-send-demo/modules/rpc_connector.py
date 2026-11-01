"""
RPC Connector - Echte RPC Connection mit Web3.py
Provider Rotation, Connection Monitoring, Real-time Block Updates
Basierend auf Web3.py Best Practices für Production-Ready Integration
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from web3 import Web3

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class RPCProvider:
    """RPC Provider Konfiguration"""
    name: str
    url: str
    chain_id: int
    priority: int  # 1 = highest priority
    timeout_seconds: int = 30
    retry_attempts: int = 3
    ws_url: str = ""  # Optional: WebSocket-Endpoint für eth_subscribe (Live-Feed)
    stablecoins: list = None  # Optional: Token-Contracts die der Live-Watcher subscribed
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'url': self.url,
            'chain_id': self.chain_id,
            'priority': self.priority,
            'timeout_seconds': self.timeout_seconds,
            'retry_attempts': self.retry_attempts,
            'ws_url': self.ws_url,
            'stablecoins': self.stablecoins or []
        }


@dataclass
class RPCStatus:
    """RPC Status"""
    provider_name: str
    chain_id: int
    is_connected: bool
    block_number: Optional[int]
    gas_price: Optional[int]
    latency_ms: Optional[float]
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    consecutive_failures: int
    
    def to_dict(self) -> dict:
        return {
            'provider_name': self.provider_name,
            'chain_id': self.chain_id,
            'is_connected': self.is_connected,
            'block_number': self.block_number,
            'gas_price': self.gas_price,
            'latency_ms': self.latency_ms,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_failure': self.last_failure.isoformat() if self.last_failure else None,
            'consecutive_failures': self.consecutive_failures
        }


class RPCConnector:
    """
    RPC Connector für echte Blockchain-Integration
    
    Features:
    - Web3.py RPC Connection zu Sepolia/Goerli Testnet
    - Provider Rotation bei Failover
    - Connection Status Monitoring
    - Real-time Block Updates
    - Gas Price Fetching
    - Timeout und Retry Logic
    """
    
    def __init__(self, providers: List[RPCProvider]):
        """
        Initialisiere RPC Connector
        
        Args:
            providers: Liste von RPC Providern (sortiert nach Priority)
        """
        self.providers = sorted(providers, key=lambda p: p.priority)
        self.web3_connections: Dict[int, Web3] = {}
        self.statuses: Dict[int, RPCStatus] = {}
        self.current_provider_index: Dict[int, int] = {}
        
        # Initialize Statuses
        for provider in self.providers:
            self.statuses[provider.chain_id] = RPCStatus(
                provider_name=provider.name,
                chain_id=provider.chain_id,
                is_connected=False,
                block_number=None,
                gas_price=None,
                latency_ms=None,
                last_success=None,
                last_failure=None,
                consecutive_failures=0
            )
        
        # Initialize Connections
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialisiere Web3 Connections"""
        for provider in self.providers:
            try:
                w3 = Web3(Web3.HTTPProvider(provider.url, request_kwargs={'timeout': provider.timeout_seconds}))
                if w3.is_connected():
                    self.web3_connections[provider.chain_id] = w3
                    self.statuses[provider.chain_id].is_connected = True
                    self.statuses[provider.chain_id].last_success = datetime.now()
                    logger.info(f"✅ Connected to {provider.name} (Chain ID: {provider.chain_id})")
                else:
                    self.statuses[provider.chain_id].last_failure = datetime.now()
                    logger.info(f"⚠️  Failed to connect to {provider.name}")
            except Exception as e:
                self.statuses[provider.chain_id].last_failure = datetime.now()
                logger.info(f"❌ Error connecting to {provider.name}: {e}")
    
    async def get_block_number(self, chain_id: int) -> int:
        """
        Hole aktuelle Block Number
        
        Args:
            chain_id: Chain ID
            
        Returns:
            Block Number
        """
        provider = self._get_active_provider(chain_id)
        if not provider:
            raise ValueError(f"No active provider for chain {chain_id}")
        
        w3 = self.web3_connections.get(chain_id)
        if not w3:
            raise ValueError(f"No connection for chain {chain_id}")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            block_number = w3.eth.block_number
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Update Status
            status = self.statuses[chain_id]
            status.block_number = block_number
            status.latency_ms = latency
            status.is_connected = True
            status.last_success = datetime.now()
            status.consecutive_failures = 0
            
            return block_number
            
        except Exception as e:
            # Update Status
            status = self.statuses[chain_id]
            status.is_connected = False
            status.last_failure = datetime.now()
            status.consecutive_failures += 1
            
            # Provider Rotation
            if status.consecutive_failures >= provider.retry_attempts:
                self._rotate_provider(chain_id)
                return await self.get_block_number(chain_id)  # Retry mit neuem Provider
            
            raise e
    
    async def get_gas_price(self, chain_id: int) -> int:
        """
        Hole aktuelle Gas Price (EIP-1559)
        
        Args:
            chain_id: Chain ID
            
        Returns:
            Gas Price in Wei
        """
        provider = self._get_active_provider(chain_id)
        if not provider:
            raise ValueError(f"No active provider for chain {chain_id}")
        
        w3 = self.web3_connections.get(chain_id)
        if not w3:
            raise ValueError(f"No connection for chain {chain_id}")
        
        try:
            # EIP-1559 Gas Price
            fee_history = w3.eth.fee_history(10)
            if fee_history:
                latest = fee_history[-1]
                gas_price = int(latest['baseFeePerGas']) + int(latest['maxPriorityFeePerGas'])
            else:
                # Fallback zu Legacy Gas Price
                gas_price = w3.eth.gas_price
            
            # Update Status
            status = self.statuses[chain_id]
            status.gas_price = gas_price
            
            return gas_price
            
        except Exception as e:
            # Update Status
            status = self.statuses[chain_id]
            status.is_connected = False
            status.last_failure = datetime.now()
            status.consecutive_failures += 1
            
            # Provider Rotation
            if status.consecutive_failures >= provider.retry_attempts:
                self._rotate_provider(chain_id)
                return await self.get_gas_price(chain_id)  # Retry mit neuem Provider
            
            raise e
    
    async def get_transaction_receipt(self, tx_hash: str, chain_id: int) -> Optional[dict]:
        """
        Hole Transaction Receipt
        
        Args:
            tx_hash: Transaction Hash
            chain_id: Chain ID
            
        Returns:
            Transaction Receipt oder None
        """
        provider = self._get_active_provider(chain_id)
        if not provider:
            raise ValueError(f"No active provider for chain {chain_id}")
        
        w3 = self.web3_connections.get(chain_id)
        if not w3:
            raise ValueError(f"No connection for chain {chain_id}")
        
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            
            # Update Status
            status = self.statuses[chain_id]
            status.is_connected = True
            status.last_success = datetime.now()
            status.consecutive_failures = 0
            
            return dict(receipt) if receipt else None
            
        except Exception as e:
            # Update Status
            status = self.statuses[chain_id]
            status.is_connected = False
            status.last_failure = datetime.now()
            status.consecutive_failures += 1
            
            # Provider Rotation
            if status.consecutive_failures >= provider.retry_attempts:
                self._rotate_provider(chain_id)
                return await self.get_transaction_receipt(tx_hash, chain_id)  # Retry mit neuem Provider
            
            raise e
    
    def _get_active_provider(self, chain_id: int) -> Optional[RPCProvider]:
        """
        Hole aktiven Provider für Chain
        
        Args:
            chain_id: Chain ID
            
        Returns:
            RPCProvider oder None
        """
        current_index = self.current_provider_index.get(chain_id, 0)
        
        for i in range(len(self.providers)):
            provider = self.providers[(current_index + i) % len(self.providers)]
            if provider.chain_id == chain_id:
                self.current_provider_index[chain_id] = (current_index + i) % len(self.providers)
                return provider
        
        return None
    
    def _rotate_provider(self, chain_id: int):
        """
        Rotiere zu nächstem Provider
        
        Args:
            chain_id: Chain ID
        """
        current_index = self.current_provider_index.get(chain_id, 0)
        next_index = (current_index + 1) % len(self.providers)
        self.current_provider_index[chain_id] = next_index
        
        next_provider = self.providers[next_index]
        logger.info(f"🔄 Rotating to {next_provider.name} for chain {chain_id}")
        
        # Reinitialize Connection
        try:
            w3 = Web3(Web3.HTTPProvider(next_provider.url, request_kwargs={'timeout': next_provider.timeout_seconds}))
            if w3.is_connected():
                self.web3_connections[chain_id] = w3
                self.statuses[chain_id].is_connected = True
                self.statuses[chain_id].last_success = datetime.now()
                self.statuses[chain_id].consecutive_failures = 0
                logger.info(f"✅ Connected to {next_provider.name}")
            else:
                self.statuses[chain_id].is_connected = False
                self.statuses[chain_id].last_failure = datetime.now()
        except Exception as e:
            logger.info(f"❌ Failed to connect to {next_provider.name}: {e}")
    
    def get_status(self, chain_id: int) -> Optional[RPCStatus]:
        """
        Hole Status für Chain
        
        Args:
            chain_id: Chain ID
            
        Returns:
            RPCStatus oder None
        """
        return self.statuses.get(chain_id)
    
    def get_all_statuses(self) -> Dict[int, RPCStatus]:
        """
        Hole Status für alle Chains
        
        Returns:
            Dict von Chain ID zu RPCStatus
        """
        return self.statuses
    
    async def monitor_connections(self):
        """Monitor alle RPC Connections"""
        while True:
            try:
                for chain_id in self.statuses.keys():
                    try:
                        await self.get_block_number(chain_id)
                    except Exception as e:
                        logger.info(f"Monitor error for chain {chain_id}: {e}")
                await asyncio.sleep(30)  # Alle 30 Sekunden prüfen
            except Exception as e:
                logger.info(f"Monitor loop error: {e}")
                await asyncio.sleep(60)


# Beispiel-Usage
async def main():
    # Erstelle RPC Provider für Sepolia Testnet
    providers = [
        RPCProvider(
            name="LlamaNodes",
            url="https://sepolia.llamarpc.com",
            chain_id=11155111,
            priority=1
        ),
        RPCProvider(
            name="Public Node",
            url="https://sepolia.public.blastapi.io",
            chain_id=11155111,
            priority=2
        ),
        RPCProvider(
            name="Infura",
            url="https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
            chain_id=11155111,
            priority=3
        )
    ]
    
    # Erstelle RPC Connector
    connector = RPCConnector(providers)
    
    # Hole Block Number
    block_number = await connector.get_block_number(11155111)
    logger.info(f"✅ Block Number: {block_number}")
    
    # Hole Gas Price
    gas_price = await connector.get_gas_price(11155111)
    logger.info(f"✅ Gas Price: {gas_price} wei")
    
    # Hole Status
    status = connector.get_status(11155111)
    logger.info(f"✅ Status: {status.provider_name} - Connected: {status.is_connected}")
    logger.info(f"   Block Number: {status.block_number}")
    logger.info(f"   Gas Price: {status.gas_price}")
    logger.info(f"   Latency: {status.latency_ms:.2f}ms")


if __name__ == "__main__":
    asyncio.run(main())