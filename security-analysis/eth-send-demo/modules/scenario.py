"""
Scenario Builder - Kontrollierte Poisoning-Szenarien für Testing
Definiert Victim, Target, Chain, Difficulty und Method
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from modules.logger import Logger

logger = Logger(__name__)


class PoisoningMethod(Enum):
    """Poisoning Methoden"""
    ZERO_VALUE = "zero_value"  # Zero-Value transferFrom
    FAKE_TOKEN = "fake_token"  # Fake-Token Contract
    DUST_TRANSFER = "dust_transfer"  # Dust Transfer (echter Token)
    HOMOGLYPH_TOKEN = "homoglyph_token"  # Unicode-Homoglyph Token


class DifficultyLevel(Enum):
    """Schwierigkeitslevel für Vanity-Generierung"""
    EASY = "4+4"  # 4 chars prefix + 4 chars suffix
    MEDIUM = "5+5"  # 5 chars prefix + 5 chars suffix
    HARD = "6+5"  # 6 chars prefix + 5 chars suffix
    EXTREME = "6+6"  # 6 chars prefix + 6 chars suffix


@dataclass
class TargetConfig:
    """Konfiguration für ein Target"""
    victim_address: str
    counterpart_address: str
    chain_id: int
    token_address: str
    target_score: float
    expected_value_usd: float
    time_window_minutes: int = 15  # Zeitfenster für Poisoning


@dataclass
class VanityConfig:
    """Konfiguration für Vanity-Generierung"""
    difficulty: DifficultyLevel
    prefix_length: int
    suffix_length: int
    target_prefix: str
    target_suffix: str
    max_attempts: int = 1000000000  # 1B attempts default
    timeout_seconds: int = 3600  # 1 hour default


@dataclass
class PoisoningScenario:
    """Vollständiges Poisoning-Szenario"""
    scenario_id: str
    name: str
    description: str
    
    # Target Konfiguration
    target: TargetConfig
    
    # Vanity Konfiguration
    vanity: VanityConfig
    
    # Poisoning Methode
    method: PoisoningMethod
    
    # Timing
    created_at: datetime
    execution_deadline: datetime
    delay_after_legitimate_tx: int = 5  # Minuten nach legitimer TX
    
    # Batch Konfiguration
    batch_size: int = 50  # Anzahl Fake-Events pro TX
    num_batches: int = 1  # Anzahl Batches
    
    # Gas Konfiguration
    max_gas_price_gwei: float = 50.0
    gas_limit: int = 1000000
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'scenario_id': self.scenario_id,
            'name': self.name,
            'description': self.description,
            'target': {
                'victim_address': self.target.victim_address,
                'counterpart_address': self.target.counterpart_address,
                'chain_id': self.target.chain_id,
                'token_address': self.target.token_address,
                'target_score': self.target.target_score,
                'expected_value_usd': self.target.expected_value_usd,
                'time_window_minutes': self.target.time_window_minutes
            },
            'vanity': {
                'difficulty': self.vanity.difficulty.value,
                'prefix_length': self.vanity.prefix_length,
                'suffix_length': self.vanity.suffix_length,
                'target_prefix': self.vanity.target_prefix,
                'target_suffix': self.vanity.target_suffix,
                'max_attempts': self.vanity.max_attempts,
                'timeout_seconds': self.vanity.timeout_seconds
            },
            'method': self.method.value,
            'created_at': self.created_at.isoformat(),
            'execution_deadline': self.execution_deadline.isoformat(),
            'delay_after_legitimate_tx': self.delay_after_legitimate_tx,
            'batch_size': self.batch_size,
            'num_batches': self.num_batches,
            'max_gas_price_gwei': self.max_gas_price_gwei,
            'gas_limit': self.gas_limit,
            'metadata': self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'PoisoningScenario':
        """Erstelle aus Dict"""
        target = TargetConfig(
            victim_address=data['target']['victim_address'],
            counterpart_address=data['target']['counterpart_address'],
            chain_id=data['target']['chain_id'],
            token_address=data['target']['token_address'],
            target_score=data['target']['target_score'],
            expected_value_usd=data['target']['expected_value_usd'],
            time_window_minutes=data['target'].get('time_window_minutes', 15)
        )
        
        vanity = VanityConfig(
            difficulty=DifficultyLevel(data['vanity']['difficulty']),
            prefix_length=data['vanity']['prefix_length'],
            suffix_length=data['vanity']['suffix_length'],
            target_prefix=data['vanity']['target_prefix'],
            target_suffix=data['vanity']['target_suffix'],
            max_attempts=data['vanity'].get('max_attempts', 1000000000),
            timeout_seconds=data['vanity'].get('timeout_seconds', 3600)
        )
        
        return cls(
            scenario_id=data['scenario_id'],
            name=data['name'],
            description=data['description'],
            target=target,
            vanity=vanity,
            method=PoisoningMethod(data['method']),
            created_at=datetime.fromisoformat(data['created_at']),
            execution_deadline=datetime.fromisoformat(data['execution_deadline']),
            delay_after_legitimate_tx=data.get('delay_after_legitimate_tx', 5),
            batch_size=data.get('batch_size', 50),
            num_batches=data.get('num_batches', 1),
            max_gas_price_gwei=data.get('max_gas_price_gwei', 50.0),
            gas_limit=data.get('gas_limit', 1000000),
            metadata=data.get('metadata', {})
        )


class ScenarioBuilder:
    """
    Scenario Builder für Poisoning-Szenarien
    
    Features:
    - Target Konfiguration
    - Vanity Konfiguration
    - Method Selection
    - Timing Configuration
    - Batch Configuration
    """
    
    def __init__(self):
        """Initialisiere Scenario Builder"""
        self.scenarios: Dict[str, PoisoningScenario] = {}
        
    def create_scenario(
        self,
        name: str,
        victim_address: str,
        counterpart_address: str,
        chain_id: int,
        token_address: str,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        method: PoisoningMethod = PoisoningMethod.ZERO_VALUE,
        **kwargs
    ) -> PoisoningScenario:
        """
        Erstelle ein neues Poisoning-Szenario
        
        Args:
            name: Name des Szenarios
            victim_address: Adresse des Victims
            counterpart_address: Adresse des Counterparts
            chain_id: Chain ID
            token_address: Token Contract Adresse
            difficulty: Schwierigkeitslevel für Vanity
            method: Poisoning Methode
            **kwargs: Zusätzliche Parameter
            
        Returns:
            PoisoningScenario
        """
        scenario_id = f"scenario_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Target Config
        target = TargetConfig(
            victim_address=victim_address,
            counterpart_address=counterpart_address,
            chain_id=chain_id,
            token_address=token_address,
            target_score=kwargs.get('target_score', 50.0),
            expected_value_usd=kwargs.get('expected_value_usd', 10000.0),
            time_window_minutes=kwargs.get('time_window_minutes', 15)
        )
        
        # Vanity Config basierend auf Difficulty
        vanity = self._create_vanity_config(
            counterpart_address,
            difficulty,
            kwargs
        )
        
        # Timing
        created_at = datetime.now()
        execution_deadline = created_at + timedelta(
            minutes=target.time_window_minutes
        )
        
        # Scenario erstellen
        scenario = PoisoningScenario(
            scenario_id=scenario_id,
            name=name,
            description=kwargs.get('description', ''),
            target=target,
            vanity=vanity,
            method=method,
            created_at=created_at,
            execution_deadline=execution_deadline,
            delay_after_legitimate_tx=kwargs.get('delay_after_legitimate_tx', 5),
            batch_size=kwargs.get('batch_size', 50),
            num_batches=kwargs.get('num_batches', 1),
            max_gas_price_gwei=kwargs.get('max_gas_price_gwei', 50.0),
            gas_limit=kwargs.get('gas_limit', 1000000),
            metadata=kwargs.get('metadata', {})
        )
        
        self.scenarios[scenario_id] = scenario
        return scenario
        
    def _create_vanity_config(
        self,
        target_address: str,
        difficulty: DifficultyLevel,
        kwargs: Dict[str, Any]
    ) -> VanityConfig:
        """Erstelle Vanity Config basierend auf Difficulty"""
        # Address normalisieren
        addr = target_address.lower()
        if addr.startswith('0x'):
            addr = addr[2:]
            
        # Prefix/Suffix Längen basierend auf Difficulty
        if difficulty == DifficultyLevel.EASY:
            prefix_len = 4
            suffix_len = 4
        elif difficulty == DifficultyLevel.MEDIUM:
            prefix_len = 5
            suffix_len = 5
        elif difficulty == DifficultyLevel.HARD:
            prefix_len = 6
            suffix_len = 5
        else:  # EXTREME
            prefix_len = 6
            suffix_len = 6
            
        # Target Prefix/Suffix
        target_prefix = addr[:prefix_len]
        target_suffix = addr[-suffix_len:] if suffix_len > 0 else ""
        
        return VanityConfig(
            difficulty=difficulty,
            prefix_length=prefix_len,
            suffix_length=suffix_len,
            target_prefix=target_prefix,
            target_suffix=target_suffix,
            max_attempts=kwargs.get('max_attempts', 1000000000),
            timeout_seconds=kwargs.get('timeout_seconds', 3600)
        )
        
    def get_scenario(self, scenario_id: str) -> Optional[PoisoningScenario]:
        """Hole ein Szenario per ID"""
        return self.scenarios.get(scenario_id)
        
    def list_scenarios(self) -> List[PoisoningScenario]:
        """Liste alle Szenarien"""
        return list(self.scenarios.values())
        
    def delete_scenario(self, scenario_id: str) -> bool:
        """Lösche ein Szenario"""
        if scenario_id in self.scenarios:
            del self.scenarios[scenario_id]
            return True
        return False
        
    def create_high_value_scenario(
        self,
        victim_address: str,
        counterpart_address: str,
        chain_id: int,
        token_address: str,
        expected_value_usd: float
    ) -> PoisoningScenario:
        """
        Erstelle High-Value Szenario (aggressiveres Poisoning)
        
        Args:
            victim_address: Adresse des Victims
            counterpart_address: Adresse des Counterparts
            chain_id: Chain ID
            token_address: Token Contract Adresse
            expected_value_usd: Erwarteter Wert in USD
            
        Returns:
            PoisoningScenario mit HARD difficulty
        """
        return self.create_scenario(
            name=f"High-Value Poisoning {victim_address[:10]}...",
            victim_address=victim_address,
            counterpart_address=counterpart_address,
            chain_id=chain_id,
            token_address=token_address,
            difficulty=DifficultyLevel.HARD,
            method=PoisoningMethod.FAKE_TOKEN,
            expected_value_usd=expected_value_usd,
            target_score=80.0,
            batch_size=100,
            num_batches=2,
            description="High-value target with aggressive poisoning"
        )
        
    def create_test_scenario(
        self,
        victim_address: str,
        counterpart_address: str,
        chain_id: int,
        token_address: str
    ) -> PoisoningScenario:
        """
        Erstelle Test-Szenario (für Development/Testing)
        
        Args:
            victim_address: Adresse des Victims
            counterpart_address: Adresse des Counterparts
            chain_id: Chain ID
            token_address: Token Contract Adresse
            
        Returns:
            PoisoningScenario mit EASY difficulty
        """
        return self.create_scenario(
            name=f"Test Poisoning {victim_address[:10]}...",
            victim_address=victim_address,
            counterpart_address=counterpart_address,
            chain_id=chain_id,
            token_address=token_address,
            difficulty=DifficultyLevel.EASY,
            method=PoisoningMethod.ZERO_VALUE,
            expected_value_usd=1000.0,
            target_score=30.0,
            batch_size=10,
            num_batches=1,
            description="Test scenario for development"
        )
        
    def export_scenario(self, scenario_id: str) -> Optional[str]:
        """Exportiere Szenario als JSON"""
        scenario = self.get_scenario(scenario_id)
        if scenario:
            return json.dumps(scenario.to_dict(), indent=2)
        return None
        
    def import_scenario(self, json_str: str) -> Optional[PoisoningScenario]:
        """Importiere Szenario aus JSON"""
        try:
            data = json.loads(json_str)
            scenario = PoisoningScenario.from_dict(data)
            self.scenarios[scenario.scenario_id] = scenario
            return scenario
        except Exception as e:
            logger.info(f"[ScenarioBuilder] Error importing scenario: {e}")
            return None


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    builder = ScenarioBuilder()
    
    # Test-Szenario erstellen
    scenario = builder.create_test_scenario(
        victim_address="0x1234567890123456789012345678901234567890",
        counterpart_address="0x0987654321098765432109876543210987654321",
        chain_id=1,
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7"
    )
    
    logger.info(f"Created scenario: {scenario.scenario_id}")
    logger.info(f"  Name: {scenario.name}")
    logger.info(f"  Method: {scenario.method.value}")
    logger.info(f"  Difficulty: {scenario.vanity.difficulty.value}")
    logger.info(f"  Target prefix: {scenario.vanity.target_prefix}")
    logger.info(f"  Target suffix: {scenario.vanity.target_suffix}")
    logger.info(f"  Batch size: {scenario.batch_size}")
    
    # High-Value Szenario
    high_value = builder.create_high_value_scenario(
        victim_address="0xABCDEF0123456789012345678901234567890ABC",
        counterpart_address="0x0987654321098765432109876543210987654321",
        chain_id=1,
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        expected_value_usd=100000.0
    )
    
    logger.info(f"\nHigh-Value scenario: {high_value.scenario_id}")
    logger.info(f"  Difficulty: {high_value.vanity.difficulty.value}")
    logger.info(f"  Expected value: ${high_value.target.expected_value_usd:,.2f}")
    
    # Export/Import
    json_str = builder.export_scenario(scenario.scenario_id)
    logger.info(f"\nExported scenario (first 200 chars):")
    logger.info(json_str[:200] + "...")
    
    # Liste aller Szenarien
    all_scenarios = builder.list_scenarios()
    logger.info(f"\nTotal scenarios: {len(all_scenarios)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())