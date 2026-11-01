"""
Shared Types für Address Poisoning Defense System
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TransferEvent:
    """Transfer Event Datenstruktur"""
    chain_id: int
    block_number: int
    tx_hash: str
    token_address: str
    from_address: str
    to_address: str
    value: int
    timestamp: datetime
    log_index: int
    block_hash: str
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'chain_id': self.chain_id,
            'block_number': self.block_number,
            'tx_hash': self.tx_hash,
            'token_address': self.token_address,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'value': str(self.value),
            'timestamp': self.timestamp.isoformat(),
            'log_index': self.log_index,
            'block_hash': self.block_hash
        }


@dataclass
class ChainConfig:
    """Konfiguration für eine Chain"""
    chain_id: int
    ws_url: str
    http_url: str
    stablecoins: list
    chain_name: str