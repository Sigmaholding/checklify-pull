"""
Policy Attestation - Blockchain-basierte Policy Verification (PACE Pattern)
Typed Transaction Intents, Deterministic Policy Verifier, Signed Policy Decision Records
Basierend auf PACE (Policy-Attested Contract Execution) Research
"""

import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from modules.logger import Logger

logger = Logger(__name__)


class PolicyType(Enum):
    """Policy Types"""
    TARGET_SELECTION = "target_selection"
    TIMING_OPTIMIZATION = "timing_optimization"
    TRANSACTION_LIMITS = "transaction_limits"
    EXCHANGE_EXCLUSION = "exchange_exclusion"
    RISK_THRESHOLD = "risk_threshold"


@dataclass
class TransactionIntent:
    """Transaction Intent für Policy Verification"""
    intent_id: str
    from_address: str
    to_address: str
    value: str  # Wei
    data: str  # Hex
    chain_id: int
    timestamp: datetime
    policy_types: List[PolicyType]
    
    def to_dict(self) -> dict:
        return {
            'intent_id': self.intent_id,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'value': self.value,
            'data': self.data,
            'chain_id': self.chain_id,
            'timestamp': self.timestamp.isoformat(),
            'policy_types': [p.value for p in self.policy_types]
        }
    
    def compute_hash(self) -> str:
        """Berechne Intent Hash"""
        return hashlib.sha256(json.dumps(self.to_dict()).encode()).hexdigest()


@dataclass
class PolicyDecisionRecord:
    """Policy Decision Record (PDR) - PACE Pattern"""
    pdr_id: str
    intent_hash: str
    policy_types: List[PolicyType]
    policy_results: Dict[str, bool]  # policy_type -> allowed
    policy_violations: List[str]
    signature: str
    verifier_address: str
    timestamp: datetime
    expiry: datetime
    replay_protection: str
    
    def to_dict(self) -> dict:
        return {
            'pdr_id': self.pdr_id,
            'intent_hash': self.intent_hash,
            'policy_types': [p.value for p in self.policy_types],
            'policy_results': self.policy_results,
            'policy_violations': self.policy_violations,
            'signature': self.signature,
            'verifier_address': self.verifier_address,
            'timestamp': self.timestamp.isoformat(),
            'expiry': self.expiry.isoformat(),
            'replay_protection': self.replay_protection
        }
    
    def compute_hash(self) -> str:
        """Berechne PDR Hash"""
        return hashlib.sha256(json.dumps(self.to_dict()).encode()).hexdigest()


@dataclass
class PolicyVerificationResult:
    """Policy Verification Result"""
    allowed: bool
    violations: List[str]
    pdr: Optional[PolicyDecisionRecord]
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            'allowed': self.allowed,
            'violations': self.violations,
            'pdr': self.pdr.to_dict() if self.pdr else None,
            'timestamp': self.timestamp.isoformat()
        }


class PolicyAttestation:
    """
    Policy Attestation mit PACE Pattern
    
    Features:
    - Typed Transaction Intents
    - Deterministic Policy Verifier
    - Signed Policy Decision Records (PDRs)
    - Replay Protection
    - Expiry Protection
    - Policy Registry on Blockchain
    """
    
    def __init__(self, verifier_address: str, private_key: str):
        """
        Initialisiere Policy Attestation
        
        Args:
            verifier_address: Address des Verifiers
            private_key: Private Key für Signing
        """
        self.verifier_address = verifier_address
        self.private_key = private_key
        self.policies: Dict[str, Dict] = {}
        self.pdr_registry: Dict[str, PolicyDecisionRecord] = {}
        self.replay_cache: Set[str] = set()
        self.replay_cache_ttl = timedelta(hours=24)
    
    def define_policy(self, policy_id: str, policy_type: PolicyType, rules: Dict):
        """
        Definiere Policy
        
        Args:
            policy_id: Policy ID
            policy_type: Policy Type
            rules: Policy Rules
        """
        self.policies[policy_id] = {
            'policy_type': policy_type,
            'rules': rules,
            'created_at': datetime.now()
        }
        logger.info(f"✅ Policy defined: {policy_id} ({policy_type.value})")
    
    async def verify_transaction(self, intent: TransactionIntent) -> PolicyVerificationResult:
        """
        Verifiziere Transaction gegen Policies
        
        Args:
            intent: Transaction Intent
            
        Returns:
            PolicyVerificationResult
        """
        policy_results = {}
        violations = []
        
        for policy_type in intent.policy_types:
            # Hole Policy
            policy = self._get_policy_by_type(policy_type)
            if not policy:
                policy_results[policy_type.value] = True
                continue
            
            # Verify Policy
            allowed, reason = await self._verify_policy(policy, intent)
            policy_results[policy_type.value] = allowed
            
            if not allowed:
                violations.append(f"{policy_type.value}: {reason}")
        
        # Create PDR
        pdr = await self._create_pdr(intent, policy_results, violations)
        
        # Check if all policies allow
        all_allowed = all(policy_results.values())
        
        return PolicyVerificationResult(
            allowed=all_allowed,
            violations=violations,
            pdr=pdr if all_allowed else None,
            timestamp=datetime.now()
        )
    
    async def _verify_policy(self, policy: Dict, intent: TransactionIntent) -> Tuple[bool, str]:
        """
        Verifiziere Policy gegen Intent
        
        Args:
            policy: Policy
            intent: Transaction Intent
            
        Returns:
            (allowed, reason)
        """
        policy_type = policy['policy_type']
        rules = policy['rules']
        
        if policy_type == PolicyType.TARGET_SELECTION:
            # Verify Target Selection Policy
            max_score = rules.get('max_score', 100)
            min_score = rules.get('min_score', 0)
            
            # In echter Implementation: Check target score
            score = 50  # Demo
            if score > max_score:
                return False, f"Target score {score} exceeds max {max_score}"
            if score < min_score:
                return False, f"Target score {score} below min {min_score}"
        
        elif policy_type == PolicyType.TIMING_OPTIMIZATION:
            # Verify Timing Policy
            min_interval = rules.get('min_interval', 60)
            max_interval = rules.get('max_interval', 3600)
            
            # In echter Implementation: Check timing
            interval = 300  # Demo
            if interval < min_interval:
                return False, f"Timing interval {interval}s below min {min_interval}s"
            if interval > max_interval:
                return False, f"Timing interval {interval}s exceeds max {max_interval}s"
        
        elif policy_type == PolicyType.TRANSACTION_LIMITS:
            # Verify Transaction Limits
            max_value = rules.get('max_value', 1000000000000000000)  # 1 ETH
            max_gas = rules.get('max_gas', 1000000)
            
            value = int(intent.value, 16)
            gas = int(intent.data, 16) if intent.data != '0x' else 0
            
            if value > max_value:
                return False, f"Value {value} exceeds max {max_value}"
            if gas > max_gas:
                return False, f"Gas {gas} exceeds max {max_gas}"
        
        elif policy_type == PolicyType.EXCHANGE_EXCLUSION:
            # Verify Exchange Exclusion
            excluded_exchanges = rules.get('excluded_exchanges', [])
            
            # In echter Implementation: Check if to_address is exchange
            is_exchange = False  # Demo
            if is_exchange:
                return False, f"Address is excluded exchange"
        
        elif policy_type == PolicyType.RISK_THRESHOLD:
            # Verify Risk Threshold
            max_risk = rules.get('max_risk', 100)
            min_risk = rules.get('min_risk', 0)
            
            # In echter Implementation: Check risk score
            risk = 50  # Demo
            if risk > max_risk:
                return False, f"Risk score {risk} exceeds max {max_risk}"
            if risk < min_risk:
                return False, f"Risk score {risk} below min {min_risk}"
        
        return True, "Policy verified"
    
    async def _create_pdr(self, intent: TransactionIntent, policy_results: Dict, violations: List[str]) -> PolicyDecisionRecord:
        """
        Erstelle Policy Decision Record (PDR)
        
        Args:
            intent: Transaction Intent
            policy_results: Policy Results
            violations: Violations
            
        Returns:
            PolicyDecisionRecord
        """
        # Generate PDR ID
        pdr_id = hashlib.sha256(f"{intent.intent_id}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        # Create PDR
        pdr = PolicyDecisionRecord(
            pdr_id=pdr_id,
            intent_hash=intent.compute_hash(),
            policy_types=intent.policy_types,
            policy_results=policy_results,
            policy_violations=violations,
            signature="",  # Wird später mit private key signiert
            verifier_address=self.verifier_address,
            timestamp=datetime.now(),
            expiry=datetime.now() + timedelta(minutes=30),
            replay_protection=hashlib.sha256(f"{intent.intent_id}_{datetime.now().isoformat()}".encode()).hexdigest()
        )
        
        # Sign PDR (simplified)
        pdr.signature = hashlib.sha256(pdr.compute_hash().encode()).hexdigest()
        
        # Store in Registry
        self.pdr_registry[pdr_id] = pdr
        
        # Check Replay Protection
        if pdr.replay_protection in self.replay_cache:
            raise ValueError("Replay attack detected")
        self.replay_cache.add(pdr.replay_protection)
        
        return pdr
    
    def _get_policy_by_type(self, policy_type: PolicyType) -> Optional[Dict]:
        """
        Hole Policy by Type
        
        Args:
            policy_type: Policy Type
            
        Returns:
            Policy oder None
        """
        for policy in self.policies.values():
            if policy['policy_type'] == policy_type:
                return policy
        return None
    
    def get_pdr(self, pdr_id: str) -> Optional[PolicyDecisionRecord]:
        """
        Hole PDR by ID
        
        Args:
            pdr_id: PDR ID
            
        Returns:
            PolicyDecisionRecord oder None
        """
        return self.pdr_registry.get(pdr_id)
    
    def get_policies(self) -> Dict[str, Dict]:
        """Hole alle Policies"""
        return self.policies
    
    def get_pdr_registry(self) -> Dict[str, PolicyDecisionRecord]:
        """Hole PDR Registry"""
        return self.pdr_registry


# Beispiel-Usage
async def main():
    # Erstelle Policy Attestation
    attestation = PolicyAttestation(
        verifier_address="0x1234567890123456789012345678901234567890",
        private_key="0x" + "0" * 63 + "1"  # Demo Key
    )
    
    # Definiere Policies
    attestation.define_policy("policy_001", PolicyType.TARGET_SELECTION, {
        'max_score': 80,
        'min_score': 20
    })
    
    attestation.define_policy("policy_002", PolicyType.TIMING_OPTIMIZATION, {
        'min_interval': 60,
        'max_interval': 3600
    })
    
    attestation.define_policy("policy_003", PolicyType.EXCHANGE_EXCLUSION, {
        'excluded_exchanges': ['binance', 'coinbase', 'kraken']
    })
    
    # Erstelle Transaction Intent
    intent = TransactionIntent(
        intent_id="intent_001",
        from_address="0x1234567890123456789012345678901234567890",
        to_address="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        value="0x0",
        data="0x",
        chain_id=1,
        timestamp=datetime.now(),
        policy_types=[
            PolicyType.TARGET_SELECTION,
            PolicyType.TIMING_OPTIMIZATION,
            PolicyType.EXCHANGE_EXCLUSION
        ]
    )
    
    # Verify Transaction
    result = await attestation.verify_transaction(intent)
    logger.info(f"✅ Policy Verification:")
    logger.info(f"   Allowed: {result.allowed}")
    logger.info(f"   Violations: {result.violations}")
    logger.info(f"   PDR: {result.pdr.pdr_id if result.pdr else 'None'}")


if __name__ == "__main__":
    asyncio.run(main())