"""
Integration Tests für Praxis-Parität Features
Testet Test-TX Detection, Timing-Optimierung, Multi-Target Processing
"""

import asyncio
import sys
sys.path.insert(0, '.')

from modules.test_tx_detector import TestTXDetector, TestTransaction
from modules.timing_optimizer import TimingOptimizer, NetworkConditions
from modules.multi_target_processor import MultiTargetProcessor
from modules.rpc_connector import RPCConnector, RPCProvider
from datetime import datetime


async def test_test_tx_detector():
    """Test Test-TX Detector"""
    print("\n=== Test Test-TX Detector ===")
    
    # Erstelle RPC Connector
    providers = [
        RPCProvider(
            name="LlamaNodes",
            url="https://sepolia.llamarpc.com",
            chain_id=11155111,
            priority=1
        )
    ]
    connector = RPCConnector(providers)
    
    # Erstelle Test-TX Detector
    detector = TestTXDetector(connector)
    
    # Füge Callback hinzu
    detected = []
    async def on_test_tx(test_tx: TestTransaction):
        detected.append(test_tx)
        print(f"✅ Test-TX detected: {test_tx.tx_hash[:10]}... (Confidence: {test_tx.confidence:.2f})")
    
    detector.add_callback(on_test_tx)
    
    # Starte Monitoring
    await detector.start_monitoring("0x1234567890123456789012345678901234567890")
    print("✅ Test-TX Detector started")
    
    # Warte kurz
    await asyncio.sleep(2)
    
    # Stoppe Monitoring
    await detector.stop_monitoring("0x1234567890123456789012345678901234567890")
    
    print("✅ Test-TX Detector Test Passed")


async def test_timing_optimizer():
    """Test Timing Optimizer"""
    print("\n=== Test Timing Optimizer ===")
    
    optimizer = TimingOptimizer()
    
    # Simuliere Network Conditions
    conditions = NetworkConditions(
        block_time_seconds=12,
        gas_price_gwei=25.0,
        network_congestion=0.6,
        mempool_size=150000,
        confirmation_depth=3
    )
    
    # Optimiere Timing
    optimization = await optimizer.optimize_timing(conditions, target_confirmation_seconds=60)
    
    print(f"✅ Timing Optimization:")
    print(f"   Optimal Delay: {optimization.optimal_delay_seconds}s")
    print(f"   Gas Price: {optimization.gas_price_gwei} Gwei")
    print(f"   Expected Confirmation: {optimization.expected_confirmation_seconds}s")
    print(f"   Confidence: {optimization.confidence:.2f}")
    
    assert optimization.expected_confirmation_seconds <= 60, "Should meet target confirmation time"
    
    print("✅ Timing Optimizer Test Passed")


async def test_multi_target_processor():
    """Test Multi-Target Processor"""
    print("\n=== Test Multi-Target Processor ===")
    
    processor = MultiTargetProcessor(max_concurrent=5, max_retries=2)
    
    # Starte Processor
    await processor.start()
    
    # Submit Tasks
    targets = [
        {'victim_address': f"0x{i:040x}", 'target_address': f"0x{i+1:040x}"}
        for i in range(10)
    ]
    
    task_ids = await processor.submit_batch(targets)
    print(f"✅ Submitted {len(task_ids)} tasks")
    
    # Warte auf Completion
    await processor.wait_for_completion(timeout_seconds=30)
    
    # Hole Status
    status = processor.get_status()
    print(f"✅ Status:")
    print(f"   Total: {status.total_targets}")
    print(f"   Completed: {status.completed_targets}")
    print(f"   Failed: {status.failed_targets}")
    print(f"   Active: {status.active_targets}")
    print(f"   Success Rate: {status.success_rate:.2%}")
    print(f"   Duration: {status.total_duration_seconds:.2f}s")
    
    # Stoppe Processor
    await processor.stop()
    
    assert status.completed_targets == 10, "All tasks should complete"
    
    print("✅ Multi-Target Processor Test Passed")


async def main():
    """Run all Integration Tests"""
    print("🚀 Starting Praxis-Parität Integration Tests")
    
    try:
        await test_test_tx_detector()
        await test_timing_optimizer()
        await test_multi_target_processor()
        
        print("\n✅ ALL TESTS PASSED!")
        print("🎉 Praxis-Parität Features are fully functional!")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())