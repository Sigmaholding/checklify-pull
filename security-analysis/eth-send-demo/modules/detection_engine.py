"""
Detection Engine - Multi-Vektor Detection für Poisoning
Fake-Token, Zero-Value/Dust, Vanity-Match, Event Cluster, Timing Anomalies
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

from modules.logger import Logger

logger = Logger(__name__)
from modules.types import TransferEvent
from modules.similarity import SimilarityEngine


@dataclass
class DetectionIndicator:
    """Detection Indicator"""
    indicator_type: str
    severity: str  # low, medium, high, critical
    confidence: float  # 0.0 - 1.0
    description: str
    evidence: dict
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'indicator_type': self.indicator_type,
            'severity': self.severity,
            'confidence': self.confidence,
            'description': self.description,
            'evidence': self.evidence,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class DetectionResult:
    """Ergebnis einer Detection-Analyse"""
    address: str
    chain_id: int
    indicators: List[DetectionIndicator]
    overall_risk_score: float  # 0.0 - 100.0
    risk_level: str  # low, medium, high, critical
    timestamp: datetime
    recommendation: str
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'address': self.address,
            'chain_id': self.chain_id,
            'indicators': [i.to_dict() for i in self.indicators],
            'overall_risk_score': self.overall_risk_score,
            'risk_level': self.risk_level,
            'timestamp': self.timestamp.isoformat(),
            'recommendation': self.recommendation
        }


class DetectionEngine:
    """
    Detection Engine für Multi-Vektor Poisoning Detection
    
    Features:
    - Fake-Token detection
    - Zero-Value/Dust detection
    - Vanity-Match detection
    - Event cluster detection
    - Timing anomaly detection
    - Multi-indicator correlation
    """
    
    # Known legitimate token contracts (simplified)
    KNOWN_TOKENS = {
        '0xdAC17F958D2ee523a2206206994597C13D831ec7',  # USDT ETH
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC ETH
        '0x55d398326f99059fF775485246999027B3197955',  # USDT BSC
        '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',  # USDC BSC
    }
    
    # Unicode homoglyph indicators
    HOMOGLYPH_INDICATORS = {
        'ꓴ',  # Homoglyph for U
        '឴',  # Khmer
        'Տ',  # Armenian
        'Т',  # Cyrillic
    }
    
    def __init__(self, similarity_engine: Optional[SimilarityEngine] = None):
        """
        Initialisiere Detection Engine
        
        Args:
            similarity_engine: Optional SimilarityEngine für Vanity-Matching
        """
        self.similarity_engine = similarity_engine or SimilarityEngine()
        
        # Known counterparties für eine Adresse (für Vanity-Matching)
        self.known_counterparties: Dict[str, Set[str]] = defaultdict(set)
        
    def analyze_event(
        self,
        event: TransferEvent,
        known_counterparts: Optional[Set[str]] = None
    ) -> DetectionResult:
        """
        Analysiere ein einzelnes Event auf Poisoning-Indikatoren
        
        Args:
            event: Das zu analysierende Event
            known_counterparts: Bekannte Counterparties der Adresse
            
        Returns:
            DetectionResult mit allen Indikatoren
        """
        indicators = []
        
        # 1. Fake-Token Detection
        fake_token_indicator = self._detect_fake_token(event)
        if fake_token_indicator:
            indicators.append(fake_token_indicator)
            
        # 2. Zero-Value/Dust Detection
        zero_value_indicator = self._detect_zero_value_dust(event)
        if zero_value_indicator:
            indicators.append(zero_value_indicator)
            
        # 3. Vanity-Match Detection
        if known_counterparts:
            vanity_indicator = self._detect_vanity_match(event, known_counterparts)
            if vanity_indicator:
                indicators.append(vanity_indicator)
                
        # 4. Timing Anomaly Detection
        timing_indicator = self._detect_timing_anomaly(event)
        if timing_indicator:
            indicators.append(timing_indicator)
            
        # Overall Risk Score berechnen
        risk_score = self._calculate_risk_score(indicators)
        risk_level = self._determine_risk_level(risk_score)
        recommendation = self._generate_recommendation(risk_level, indicators)
        
        return DetectionResult(
            address=event.to_address,  # Victim ist normalerweise to_address
            chain_id=event.chain_id,
            indicators=indicators,
            overall_risk_score=risk_score,
            risk_level=risk_level,
            timestamp=datetime.now(),
            recommendation=recommendation
        )
        
    def analyze_events_batch(
        self,
        events: List[TransferEvent],
        address: str
    ) -> DetectionResult:
        """
        Analysiere mehrere Events für eine Adresse
        
        Args:
            events: Liste der Events
            address: Die zu analysierende Adresse
            
        Returns:
            DetectionResult mit allen Indikatoren
        """
        indicators = []
        
        # Known counterparties extrahieren
        known_counterparts = self._extract_counterparties(events, address)
        
        # Event Cluster Detection
        cluster_indicator = self._detect_event_cluster(events)
        if cluster_indicator:
            indicators.append(cluster_indicator)
            
        # Einzelne Events analysieren
        for event in events:
            # Nur Events analysieren die die Adresse betreffen
            if event.from_address.lower() == address.lower() or \
               event.to_address.lower() == address.lower():
                
                event_indicators = self.analyze_event(event, known_counterparts)
                indicators.extend(event_indicators.indicators)
                
        # Overall Risk Score
        risk_score = self._calculate_risk_score(indicators)
        risk_level = self._determine_risk_level(risk_score)
        recommendation = self._generate_recommendation(risk_level, indicators)
        
        return DetectionResult(
            address=address,
            chain_id=events[0].chain_id if events else 0,
            indicators=indicators,
            overall_risk_score=risk_score,
            risk_level=risk_level,
            timestamp=datetime.now(),
            recommendation=recommendation
        )
        
    def _detect_fake_token(self, event: TransferEvent) -> Optional[DetectionIndicator]:
        """Erkenne Fake-Token Transfers"""
        # Prüfe ob Token Contract bekannt ist
        if event.token_address.lower() not in [t.lower() for t in self.KNOWN_TOKENS]:
            # Token ist nicht in der known list
            return DetectionIndicator(
                indicator_type="fake_token",
                severity="high",
                confidence=0.8,
                description="Transfer from unknown token contract",
                evidence={
                    'token_address': event.token_address,
                    'known_tokens': list(self.KNOWN_TOKENS)
                },
                timestamp=datetime.now()
            )
            
        # Prüfe auf Unicode-Homoglyphs im Token Symbol
        # (In einer echten Implementation würde dies Token Metadata prüfen)
        return None
        
    def _detect_zero_value_dust(self, event: TransferEvent) -> Optional[DetectionIndicator]:
        """Erkenne Zero-Value oder Dust Transfers"""
        # Zero-Value
        if event.value == 0:
            return DetectionIndicator(
                indicator_type="zero_value",
                severity="medium",
                confidence=0.9,
                description="Zero-value transfer (potential poisoning)",
                evidence={
                    'value': str(event.value),
                    'from_address': event.from_address,
                    'to_address': event.to_address
                },
                timestamp=datetime.now()
            )
            
        # Dust (< 0.01 USDT = 10000 bei 6 decimals)
        if event.value < 10000:
            return DetectionIndicator(
                indicator_type="dust_transfer",
                severity="low",
                confidence=0.7,
                description="Dust transfer (potential poisoning)",
                evidence={
                    'value': str(event.value),
                    'from_address': event.from_address,
                    'to_address': event.to_address
                },
                timestamp=datetime.now()
            )
            
        return None
        
    def _detect_vanity_match(
        self,
        event: TransferEvent,
        known_counterparts: Set[str]
    ) -> Optional[DetectionIndicator]:
        """Erkenne Vanity-Matching gegen bekannte Counterparties"""
        for known in known_counterparts:
            # Vergleiche counterpart mit known counterparties
            if event.from_address.lower() != known.lower():
                similarity = self.similarity_engine.compare_addresses(
                    event.from_address,
                    known
                )
                
                if similarity.is_lookalike(threshold=0.7):
                    return DetectionIndicator(
                        indicator_type="vanity_match",
                        severity="high",
                        confidence=similarity.overall_score,
                        description=f"Lookalike address detected (score: {similarity.overall_score:.2f})",
                        evidence={
                            'known_address': known,
                            'lookalike_address': event.from_address,
                            'prefix_match': similarity.prefix_match,
                            'suffix_match': similarity.suffix_match,
                            'has_homoglyphs': similarity.has_homoglyphs
                        },
                        timestamp=datetime.now()
                    )
                    
        return None
        
    def _detect_timing_anomaly(self, event: TransferEvent) -> Optional[DetectionIndicator]:
        """Erkenne Timing Anomalien"""
        # In einer echten Implementation würde dies historische Daten analysieren
        # Hier simplified logic
        
        # Prüfe ob Event in ungewöhnlicher Zeit aufgetreten ist
        current_hour = datetime.now().hour
        
        # Anomalie: Events zwischen 2-5 Uhr UTC (niedrige Aktivität)
        if 2 <= current_hour <= 5:
            return DetectionIndicator(
                indicator_type="timing_anomaly",
                severity="low",
                confidence=0.5,
                description="Event during low-activity hours",
                evidence={
                    'hour': current_hour,
                    'timestamp': event.timestamp.isoformat()
                },
                timestamp=datetime.now()
            )
            
        return None
        
    def _detect_event_cluster(self, events: List[TransferEvent]) -> Optional[DetectionIndicator]:
        """Erkenne Event Clustering"""
        if len(events) < 5:
            return None
            
        # Prüfe ob viele Events in kurzer Zeit
        time_window = timedelta(minutes=5)
        event_times = [e.timestamp for e in events]
        
        # Sortieren
        event_times.sort()
        
        # Prüfe für Cluster
        for i in range(len(event_times) - 4):
            window_events = event_times[i:i+5]
            if max(window_events) - min(window_events) < time_window:
                return DetectionIndicator(
                    indicator_type="event_cluster",
                    severity="medium",
                    confidence=0.8,
                    description="Multiple events in short time window",
                    evidence={
                        'event_count': 5,
                        'time_window_minutes': 5,
                        'events': [e.tx_hash for e in events[i:i+5]]
                    },
                    timestamp=datetime.now()
                )
                
        return None
        
    def _calculate_risk_score(self, indicators: List[DetectionIndicator]) -> float:
        """Berechne Overall Risk Score"""
        if not indicators:
            return 0.0
            
        # Gewichtung nach Severity
        severity_weights = {
            'critical': 100.0,
            'high': 75.0,
            'medium': 50.0,
            'low': 25.0
        }
        
        total_score = 0.0
        for indicator in indicators:
            base_score = severity_weights.get(indicator.severity, 25.0)
            weighted_score = base_score * indicator.confidence
            total_score += weighted_score
            
        # Normalisieren auf 0-100
        max_possible = len(indicators) * 100.0
        normalized = (total_score / max_possible) * 100.0 if max_possible > 0 else 0.0
        
        return min(normalized, 100.0)
        
    def _determine_risk_level(self, risk_score: float) -> str:
        """Bestimme Risk Level basierend auf Score"""
        if risk_score >= 75:
            return "critical"
        elif risk_score >= 50:
            return "high"
        elif risk_score >= 25:
            return "medium"
        else:
            return "low"
            
    def _generate_recommendation(
        self,
        risk_level: str,
        indicators: List[DetectionIndicator]
    ) -> str:
        """Generiere Empfehlung basierend auf Risk Level"""
        if risk_level == "critical":
            return "CRITICAL: Immediate action required. Do not use this address. Contact security team."
        elif risk_level == "high":
            return "HIGH: Strong evidence of poisoning. Verify all transactions before proceeding."
        elif risk_level == "medium":
            return "MEDIUM: Suspicious activity detected. Exercise caution and verify recipient addresses."
        else:
            return "LOW: Some suspicious indicators but likely safe. Standard verification recommended."
            
    def _extract_counterparties(
        self,
        events: List[TransferEvent],
        address: str
    ) -> Set[str]:
        """Extrahiere bekannte Counterparties"""
        counterparties = set()
        
        for event in events:
            if event.from_address.lower() == address.lower():
                counterparties.add(event.to_address)
            elif event.to_address.lower() == address.lower():
                counterparties.add(event.from_address)
                
        return counterparties
        
    def add_known_counterparties(self, address: str, counterparties: Set[str]):
        """Füge bekannte Counterparties für eine Adresse hinzu"""
        self.known_counterparties[address.lower()].update(counterparties)
        
    def get_known_counterparties(self, address: str) -> Set[str]:
        """Hole bekannte Counterparties für eine Adresse"""
        return self.known_counterparties.get(address.lower(), set())


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    from modules.types import TransferEvent
    from modules.similarity import SimilarityEngine
    
    # Detection Engine
    similarity_engine = SimilarityEngine()
    engine = DetectionEngine(similarity_engine)
    
    # Beispiel Event
    event = TransferEvent(
        chain_id=1,
        block_number=12345678,
        tx_hash="0xabc123",
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        from_address="0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1",
        to_address="0x1234567890123456789012345678901234567890",
        value=0,  # Zero value
        timestamp=datetime.now(),
        log_index=0,
        block_hash="0xdef456"
    )
    
    # Analysieren
    result = engine.analyze_event(event)
    
    logger.info(f"Detection Result for {result.address}:")
    logger.info(f"  Risk Score: {result.overall_risk_score:.1f}/100")
    logger.info(f"  Risk Level: {result.risk_level}")
    logger.info(f"  Indicators: {len(result.indicators)}")
    
    for indicator in result.indicators:
        logger.info(f"    - {indicator.indicator_type}: {indicator.severity} ({indicator.confidence:.2f})")
        logger.info(f"      {indicator.description}")
        
    logger.info(f"  Recommendation: {result.recommendation}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())