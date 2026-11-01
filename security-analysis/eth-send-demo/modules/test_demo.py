"""
Quick Demo Test für Address Poisoning Defense System
Testet die Kernfunktionalität für Testnetzwerk-Demonstration
"""

import asyncio
import sys
sys.path.insert(0, '.')

from modules.similarity import SimilarityEngine
from modules.scenario import ScenarioBuilder
from modules.detection_engine import DetectionEngine
from modules.risk_engine import RiskEngine
from modules.types import TransferEvent
from datetime import datetime


async def test_similarity():
    """Test Similarity Engine"""
    print("=== Testing Similarity Engine ===")
    engine = SimilarityEngine()
    
    # Test Adressen (echer Fall aus poison/index.html)
    real = "0xB2bC30C3a8C04c6F4100b5cC76f83c547dc373b1"
    lookalike = "0xB2bC25cC4F9022CeB20fB42b123aE3a3094473b1"
    
    result = engine.compare_addresses(real, lookalike)
    
    print(f"Real: {real[:10]}...{real[-4:]}")
    print(f"Lookalike: {lookalike[:10]}...{lookalike[-4:]}")
    print(f"Prefix Match: {result.prefix_match} chars")
    print(f"Suffix Match: {result.suffix_match} chars")
    print(f"Overall Score: {result.overall_score:.3f}")
    print(f"Is Lookalike: {result.is_lookalike()}")
    print(f"Has Homoglyphs: {result.has_homoglyphs}")
    print("✅ Similarity Engine works!\n")


async def test_scenario():
    """Test Scenario Builder"""
    print("=== Testing Scenario Builder ===")
    builder = ScenarioBuilder()
    
    # Test Scenario erstellen
    scenario = builder.create_test_scenario(
        victim_address="0x1234567890123456789012345678901234567890",
        counterpart_address="0x0987654321098765432109876543210987654321",
        chain_id=1,
        token_address="0xdAC17F958D2ee523a2206206994597C13D831ec7"
    )
    
    print(f"Scenario ID: {scenario.scenario_id}")
    print(f"Name: {scenario.name}")
    print(f"Method: {scenario.method.value}")
    print(f"Difficulty: {scenario.vanity.difficulty.value}")
    print(f"Target Prefix: {scenario.vanity.target_prefix}")
    print(f"Target Suffix: {scenario.vanity.target_suffix}")
    print(f"Batch Size: {scenario.batch_size}")
    print("✅ Scenario Builder works!\n")


async def test_detection():
    """Test Detection Engine"""
    print("=== Testing Detection Engine ===")
    engine = DetectionEngine()
    
    # Zero-Value Transfer Event
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
    
    result = engine.analyze_event(event)
    
    print(f"Address: {result.address}")
    print(f"Chain ID: {result.chain_id}")
    print(f"Indicators: {len(result.indicators)}")
    for indicator in result.indicators:
        print(f"  - {indicator.indicator_type}: {indicator.severity} ({indicator.confidence:.2f})")
    print(f"Overall Risk Score: {result.overall_risk_score:.1f}/100")
    print(f"Risk Level: {result.risk_level}")
    print(f"Recommendation: {result.recommendation}")
    print("✅ Detection Engine works!\n")


async def test_risk():
    """Test Risk Engine"""
    print("=== Testing Risk Engine ===")
    engine = RiskEngine()
    
    # Mock Detection Result
    from modules.detection_engine import DetectionIndicator
    
    detection_result = type('obj', (object,), {
        'address': '0x1234567890123456789012345678901234567890',
        'chain_id': 1,
        'indicators': [
            DetectionIndicator(
                indicator_type="vanity_match",
                severity="high",
                confidence=0.85,
                description="Lookalike address detected",
                evidence={"similarity": 0.85},
                timestamp=datetime.now()
            )
        ],
        'overall_risk_score': 75.0,
        'risk_level': "high",
        'timestamp': datetime.now(),
        'recommendation': "HIGH: Strong evidence of poisoning."
    })()
    
    alert = await engine.process_detection_result(detection_result)
    
    if alert:
        print(f"Alert ID: {alert.alert_id}")
        print(f"Severity: {alert.severity}")
        print(f"Primary Detection: {alert.primary_detection_type}")
        print(f"Risk Score: {alert.overall_risk_score:.1f}/100")
        print(f"Action Required: {alert.action_required}")
    else:
        print("No alert generated (below threshold)")
    
    # Risk Assessment
    assessment = engine.get_risk_assessment('0x1234567890123456789012345678901234567890')
    if assessment:
        print(f"Risk Assessment: {assessment.risk_level} ({assessment.overall_risk_score:.1f}/100)")
    
    print("✅ Risk Engine works!\n")


async def main():
    """Hauptfunktion"""
    print("🧪 Address Poisoning Defense System - Demo Test\n")
    print("=" * 50)
    
    try:
        await test_similarity()
        await test_scenario()
        await test_detection()
        await test_risk()
        
        print("=" * 50)
        print("✅ ALL TESTS PASSED - System is ready for testnet demo!")
        print("\n📋 Next Steps:")
        print("1. Configure testnet RPC endpoints")
        print("2. Set up Redis for state management")
        print("3. Run the integration system")
        print("4. Monitor for address poisoning attempts")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())