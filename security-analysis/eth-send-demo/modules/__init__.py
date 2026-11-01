"""
Address Poisoning Defense System - Complete Module Package
Produktionsreifes Multi-Chain Defense System gegen Address Poisoning Angriffe
"""

from modules.watcher import BlockchainWatcher
from modules.types import ChainConfig, TransferEvent
from modules.indexer import TransferIndexer, IndexerStats
from modules.profiler import AddressProfiler, AddressProfile, CounterpartyProfile
from modules.similarity import SimilarityEngine, SimilarityResult, MatchPattern
from modules.scenario import ScenarioBuilder, PoisoningScenario, PoisoningMethod, DifficultyLevel
from modules.transaction_builder import TransactionBuilder, TransactionData, FakeTokenContract
from modules.chain_adapter import ChainAdapter, BlockData, LogData
from modules.detection_watcher import DetectionWatcher, MonitoredAddress, DetectionAlert
from modules.detection_engine import DetectionEngine, DetectionIndicator, DetectionResult
from modules.risk_engine import RiskEngine, RiskAssessment, CorrelatedAlert, NotificationChannel

__version__ = "1.0.0"
__author__ = "Security Research Team"
__description__ = "Production-grade address poisoning defense system"

__all__ = [
    # Watcher
    'BlockchainWatcher',
    'ChainConfig',
    'TransferEvent',
    
    # Indexer
    'TransferIndexer',
    'IndexerStats',
    
    # Profiler
    'AddressProfiler',
    'AddressProfile',
    'CounterpartyProfile',
    
    # Similarity
    'SimilarityEngine',
    'SimilarityResult',
    'MatchPattern',
    
    # Scenario
    'ScenarioBuilder',
    'PoisoningScenario',
    'PoisoningMethod',
    'DifficultyLevel',
    
    # Transaction Builder
    'TransactionBuilder',
    'TransactionData',
    'FakeTokenContract',
    
    # Chain Adapter
    'ChainAdapter',
    'BlockData',
    'LogData',
    
    # Detection Watcher
    'DetectionWatcher',
    'MonitoredAddress',
    'DetectionAlert',
    
    # Detection Engine
    'DetectionEngine',
    'DetectionIndicator',
    'DetectionResult',
    
    # Risk Engine
    'RiskEngine',
    'RiskAssessment',
    'CorrelatedAlert',
    'NotificationChannel',
]