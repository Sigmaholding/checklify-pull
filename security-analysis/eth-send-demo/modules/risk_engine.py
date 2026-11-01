"""
Risk Engine - Korrelation und Alarm für Detection-Ergebnisse
Multi-indicator correlation, Risk scoring, Alert generation, Notification dispatch
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import json

from modules.logger import Logger

logger = Logger(__name__)
from modules.detection_engine import DetectionResult, DetectionIndicator


@dataclass
class RiskAssessment:
    """Risk Assessment für eine Adresse"""
    address: str
    overall_risk_score: float  # 0.0 - 100.0
    risk_level: str  # low, medium, high, critical
    indicator_count: int
    critical_indicators: int
    high_indicators: int
    medium_indicators: int
    low_indicators: int
    last_assessment: datetime
    trend: str  # improving, stable, deteriorating
    recommendation: str
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'address': self.address,
            'overall_risk_score': self.overall_risk_score,
            'risk_level': self.risk_level,
            'indicator_count': self.indicator_count,
            'critical_indicators': self.critical_indicators,
            'high_indicators': self.high_indicators,
            'medium_indicators': self.medium_indicators,
            'low_indicators': self.low_indicators,
            'last_assessment': self.last_assessment.isoformat(),
            'trend': self.trend,
            'recommendation': self.recommendation
        }


@dataclass
class CorrelatedAlert:
    """Korrelierter Alert über mehrere Indikatoren"""
    alert_id: str
    address: str
    chain_ids: List[int]
    primary_detection_type: str
    correlated_indicators: List[DetectionIndicator]
    overall_risk_score: float
    severity: str
    timestamp: datetime
    context: dict
    action_required: bool
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'alert_id': self.alert_id,
            'address': self.address,
            'chain_ids': self.chain_ids,
            'primary_detection_type': self.primary_detection_type,
            'correlated_indicators': [i.to_dict() for i in self.correlated_indicators],
            'overall_risk_score': self.overall_risk_score,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'action_required': self.action_required
        }


@dataclass
class NotificationChannel:
    """Notification Channel Konfiguration"""
    channel_type: str  # email, slack, webhook, sms
    enabled: bool
    config: dict
    min_severity: str  # minimum severity to notify
    
    def to_dict(self) -> dict:
        """Konvertiere zu Dict"""
        return {
            'channel_type': self.channel_type,
            'enabled': self.enabled,
            'config': self.config,
            'min_severity': self.min_severity
        }


class RiskEngine:
    """
    Risk Engine für Korrelation und Alarm
    
    Features:
    - Multi-indicator correlation
    - Risk scoring
    - Alert generation
    - Severity classification
    - Notification dispatch
    - Trend analysis
    """
    
    # Severity levels in order of severity
    SEVERITY_LEVELS = ['low', 'medium', 'high', 'critical']
    
    def __init__(
        self,
        notification_callback: Optional[Callable[[CorrelatedAlert], None]] = None,
        storage_client=None
    ):
        """
        Initialisiere Risk Engine
        
        Args:
            notification_callback: Callback für Notifications
            storage_client: Storage Client für Alert-Persistenz
        """
        self.notification_callback = notification_callback
        self.storage = storage_client
        
        # Risk Assessments per Address
        self.risk_assessments: Dict[str, RiskAssessment] = {}
        
        # Historical assessments für Trend analysis
        self.assessment_history: Dict[str, List[RiskAssessment]] = defaultdict(list)
        
        # Notification Channels
        self.notification_channels: Dict[str, NotificationChannel] = {}
        
        # Alert Cooldown (verhindert Alert-Spam)
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.cooldown_period = timedelta(minutes=15)
        
    async def process_detection_result(
        self,
        detection_result: DetectionResult
    ) -> Optional[CorrelatedAlert]:
        """
        Verarbeite Detection Result und generiere korrelierten Alert
        
        Args:
            detection_result: Detection Result von Detection Engine
            
        Returns:
            CorrelatedAlert oder None wenn kein Alert nötig
        """
        # Risk Assessment aktualisieren
        assessment = self._update_risk_assessment(detection_result)
        
        # Prüfe ob Alert nötig
        if self._should_alert(assessment):
            # Korrelierten Alert generieren
            alert = self._generate_correlated_alert(detection_result, assessment)
            
            # Notification dispatch
            await self._dispatch_notification(alert)
            
            # Alert speichern
            if self.storage:
                await self._store_alert(alert)
                
            return alert
            
        return None
        
    def _update_risk_assessment(
        self,
        detection_result: DetectionResult
    ) -> RiskAssessment:
        """Aktualisiere Risk Assessment für eine Adresse"""
        address = detection_result.address
        
        # Indikatoren zählen
        critical_count = sum(1 for i in detection_result.indicators if i.severity == 'critical')
        high_count = sum(1 for i in detection_result.indicators if i.severity == 'high')
        medium_count = sum(1 for i in detection_result.indicators if i.severity == 'medium')
        low_count = sum(1 for i in detection_result.indicators if i.severity == 'low')
        
        # Trend analysieren
        trend = self._analyze_trend(address, detection_result.overall_risk_score)
        
        # Assessment erstellen
        assessment = RiskAssessment(
            address=address,
            overall_risk_score=detection_result.overall_risk_score,
            risk_level=detection_result.risk_level,
            indicator_count=len(detection_result.indicators),
            critical_indicators=critical_count,
            high_indicators=high_count,
            medium_indicators=medium_count,
            low_indicators=low_count,
            last_assessment=datetime.now(),
            trend=trend,
            recommendation=detection_result.recommendation
        )
        
        # Speichern
        self.risk_assessments[address] = assessment
        
        # History für Trend analysis
        self.assessment_history[address].append(assessment)
        if len(self.assessment_history[address]) > 10:  # Max 10 Einträge
            self.assessment_history[address].pop(0)
            
        return assessment
        
    def _analyze_trend(self, address: str, current_score: float) -> str:
        """Analysiere Trend basierend auf historischen Assessments"""
        history = self.assessment_history.get(address, [])
        
        if len(history) < 2:
            return "stable"
            
        # Durchschnitt der letzten 3 Assessments
        recent_scores = [a.overall_risk_score for a in history[-3:]]
        avg_recent = sum(recent_scores) / len(recent_scores)
        
        # Trend bestimmen
        if current_score > avg_recent + 10:
            return "deteriorating"
        elif current_score < avg_recent - 10:
            return "improving"
        else:
            return "stable"
            
    def _should_alert(self, assessment: RiskAssessment) -> bool:
        """Prüfe ob Alert generiert werden soll"""
        # Cooldown prüfen
        if assessment.address in self.alert_cooldowns:
            if datetime.now() - self.alert_cooldowns[assessment.address] < self.cooldown_period:
                return False
                
        # Severity prüfen
        if assessment.risk_level in ['high', 'critical']:
            return True
            
        # Medium mit kritischen Indikatoren
        if assessment.risk_level == 'medium' and assessment.critical_indicators > 0:
            return True
            
        return False
        
    def _generate_correlated_alert(
        self,
        detection_result: DetectionResult,
        assessment: RiskAssessment
    ) -> CorrelatedAlert:
        """Generiere korrelierten Alert"""
        alert_id = f"risk_alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{assessment.address[:8]}"
        
        # Primary detection type (höchste severity)
        primary_type = self._get_primary_detection_type(detection_result.indicators)
        
        # Context
        context = {
            'trend': assessment.trend,
            'indicator_breakdown': {
                'critical': assessment.critical_indicators,
                'high': assessment.high_indicators,
                'medium': assessment.medium_indicators,
                'low': assessment.low_indicators
            },
            'recommendation': assessment.recommendation
        }
        
        alert = CorrelatedAlert(
            alert_id=alert_id,
            address=assessment.address,
            chain_ids=[detection_result.chain_id],
            primary_detection_type=primary_type,
            correlated_indicators=detection_result.indicators,
            overall_risk_score=assessment.overall_risk_score,
            severity=assessment.risk_level,
            timestamp=datetime.now(),
            context=context,
            action_required=assessment.risk_level in ['high', 'critical']
        )
        
        # Cooldown setzen
        self.alert_cooldowns[assessment.address] = datetime.now()
        
        return alert
        
    def _get_primary_detection_type(self, indicators: List[DetectionIndicator]) -> str:
        """Bestimme primären Detection Type"""
        if not indicators:
            return "unknown"
            
        # Sortiere nach severity (critical first)
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_indicators = sorted(
            indicators,
            key=lambda i: severity_order.get(i.severity, 4)
        )
        
        return sorted_indicators[0].indicator_type
        
    async def _dispatch_notification(self, alert: CorrelatedAlert):
        """Dispatch Notification über konfigurierte Channels"""
        # Callback aufrufen
        if self.notification_callback:
            self.notification_callback(alert)
            
        # Channel-basierte Notifications
        for channel_id, channel in self.notification_channels.items():
            if not channel.enabled:
                continue
                
            # Severity prüfen
            if not self._meets_severity_threshold(alert.severity, channel.min_severity):
                continue
                
            # Notification senden
            await self._send_channel_notification(alert, channel)
            
    def _meets_severity_threshold(self, alert_severity: str, min_severity: str) -> bool:
        """Prüfe ob Alert Severity Threshold erreicht"""
        alert_index = self.SEVERITY_LEVELS.index(alert_severity)
        min_index = self.SEVERITY_LEVELS.index(min_severity)
        return alert_index >= min_index
        
    async def _send_channel_notification(self, alert: CorrelatedAlert, channel: NotificationChannel):
        """Sende Notification über spezifischen Channel"""
        try:
            if channel.channel_type == 'email':
                await self._send_email_notification(alert, channel.config)
            elif channel.channel_type == 'slack':
                await self._send_slack_notification(alert, channel.config)
            elif channel.channel_type == 'webhook':
                await self._send_webhook_notification(alert, channel.config)
            elif channel.channel_type == 'sms':
                await self._send_sms_notification(alert, channel.config)
                
        except Exception as e:
            logger.info(f"[RiskEngine] Error sending notification via {channel.channel_type}: {e}")
            
    async def _send_email_notification(self, alert: CorrelatedAlert, config: dict):
        """Sende Email Notification"""
        # Placeholder für echte Email-Integration
        logger.info(f"[RiskEngine] EMAIL ALERT: {alert.alert_id}")
        logger.info(f"  To: {config.get('to')}")
        logger.info(f"  Subject: Security Alert - {alert.severity.upper()}")
        logger.info(f"  Address: {alert.address}")
        logger.info(f"  Risk Score: {alert.overall_risk_score:.1f}/100")
        
    async def _send_slack_notification(self, alert: CorrelatedAlert, config: dict):
        """Sende Slack Notification"""
        # Placeholder für echte Slack-Integration
        logger.info(f"[RiskEngine] SLACK ALERT: {alert.alert_id}")
        logger.info(f"  Webhook: {config.get('webhook_url')}")
        logger.info(f"  Channel: {config.get('channel')}")
        logger.info(f"  Message: Security Alert - {alert.address} - {alert.severity}")
        
    async def _send_webhook_notification(self, alert: CorrelatedAlert, config: dict):
        """Sende Webhook Notification"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = alert.to_dict()
            
            async with session.post(
                config['url'],
                json=payload,
                headers=config.get('headers', {})
            ) as response:
                if response.status != 200:
                    logger.info(f"[RiskEngine] Webhook failed: {response.status}")
                    
    async def _send_sms_notification(self, alert: CorrelatedAlert, config: dict):
        """Sende SMS Notification"""
        # Placeholder für echte SMS-Integration
        logger.info(f"[RiskEngine] SMS ALERT: {alert.alert_id}")
        logger.info(f"  To: {config.get('phone')}")
        logger.info(f"  Message: Security Alert - {alert.address} - {alert.severity}")
        
    async def _store_alert(self, alert: CorrelatedAlert):
        """Speichere Alert in Storage"""
        try:
            key = f"risk_alerts:{alert.alert_id}"
            await self.storage.set(key, json.dumps(alert.to_dict()))
        except Exception as e:
            logger.info(f"[RiskEngine] Error storing alert: {e}")
            
    def add_notification_channel(
        self,
        channel_id: str,
        channel_type: str,
        config: dict,
        min_severity: str = 'high',
        enabled: bool = True
    ):
        """
        Füge Notification Channel hinzu
        
        Args:
            channel_id: Eindeutige Channel ID
            channel_type: Channel Typ (email, slack, webhook, sms)
            config: Channel-spezifische Konfiguration
            min_severity: Minimale Severity für Notifications
            enabled: Ob Channel aktiviert ist
        """
        channel = NotificationChannel(
            channel_type=channel_type,
            enabled=enabled,
            config=config,
            min_severity=min_severity
        )
        
        self.notification_channels[channel_id] = channel
        logger.info(f"[RiskEngine] Added notification channel: {channel_id} ({channel_type})")
        
    def remove_notification_channel(self, channel_id: str):
        """Entferne Notification Channel"""
        if channel_id in self.notification_channels:
            del self.notification_channels[channel_id]
            logger.info(f"[RiskEngine] Removed notification channel: {channel_id}")
            
    def get_risk_assessment(self, address: str) -> Optional[RiskAssessment]:
        """Hole Risk Assessment für eine Adresse"""
        return self.risk_assessments.get(address)
        
    def get_all_risk_assessments(self) -> List[RiskAssessment]:
        """Hole alle Risk Assessments"""
        return list(self.risk_assessments.values())
        
    def get_high_risk_addresses(self, min_score: float = 50.0) -> List[RiskAssessment]:
        """Hole alle High-Risk Adressen"""
        return [
            assessment for assessment in self.risk_assessments.values()
            if assessment.overall_risk_score >= min_score
        ]


# Mock Storage Client für Testing
class MockStorage:
    """Mock Storage Client"""
    def __init__(self):
        self.data = {}
        
    async def set(self, key: str, value: str):
        self.data[key] = value
        
    async def get(self, key: str) -> Optional[str]:
        return self.data.get(key)


# Beispiel-Usage
async def main():
    """Beispiel-Usage"""
    from modules.detection_engine import DetectionEngine, DetectionIndicator
    from modules.types import TransferEvent
    
    # Mock Storage
    storage = MockStorage()
    
    # Notification Callback
    def handle_notification(alert: CorrelatedAlert):
        logger.info(f"[NOTIFICATION] {alert.alert_id}: {alert.address} - {alert.severity}")
    
    # Risk Engine
    engine = RiskEngine(
        notification_callback=handle_notification,
        storage_client=storage
    )
    
    # Notification Channel hinzufügen
    engine.add_notification_channel(
        channel_id="slack_main",
        channel_type="slack",
        config={
            "webhook_url": "https://hooks.slack.com/services/...",
            "channel": "#security-alerts"
        },
        min_severity="high"
    )
    
    # Mock Detection Result
    detection_result = DetectionResult(
        address="0x1234567890123456789012345678901234567890",
        chain_id=1,
        indicators=[
            DetectionIndicator(
                indicator_type="vanity_match",
                severity="high",
                confidence=0.85,
                description="Lookalike address detected",
                evidence={"similarity": 0.85},
                timestamp=datetime.now()
            ),
            DetectionIndicator(
                indicator_type="zero_value",
                severity="medium",
                confidence=0.9,
                description="Zero-value transfer",
                evidence={"value": "0"},
                timestamp=datetime.now()
            )
        ],
        overall_risk_score=75.0,
        risk_level="high",
        timestamp=datetime.now(),
        recommendation="HIGH: Strong evidence of poisoning. Verify all transactions."
    )
    
    # Verarbeiten
    alert = await engine.process_detection_result(detection_result)
    
    if alert:
        logger.info(f"Generated correlated alert: {alert.alert_id}")
        logger.info(f"  Severity: {alert.severity}")
        logger.info(f"  Risk Score: {alert.overall_risk_score:.1f}/100")
        logger.info(f"  Action Required: {alert.action_required}")
        
    # Risk Assessment holen
    assessment = engine.get_risk_assessment("0x1234567890123456789012345678901234567890")
    if assessment:
        logger.info(f"\nRisk Assessment:")
        logger.info(f"  Risk Level: {assessment.risk_level}")
        logger.info(f"  Trend: {assessment.trend}")
        logger.info(f"  Recommendation: {assessment.recommendation}")


if __name__ == "__main__":
    asyncio.run(main())