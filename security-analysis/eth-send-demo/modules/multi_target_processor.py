"""
Multi-Target Processor - Parallel Processing für 10+ Targets
Queue Management, Load Balancing, Progress Tracking per Target
Basierend auf State-of-the-Art Distributed Processing Research
"""

import asyncio
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from modules.logger import Logger

logger = Logger(__name__)


class TargetStatus(Enum):
    """Target Status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TargetTask:
    """Target Task"""
    task_id: str
    victim_address: str
    target_address: str
    status: TargetStatus
    priority: int  # 1 = highest
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    retry_count: int
    progress: float  # 0-1
    
    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'victim_address': self.victim_address,
            'target_address': self.target_address,
            'status': self.status.value,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'retry_count': self.retry_count,
            'progress': self.progress
        }


@dataclass
class MultiTargetResult:
    """Multi-Target Result"""
    process_id: str
    total_targets: int
    completed_targets: int
    failed_targets: int
    active_targets: int
    total_duration_seconds: float
    success_rate: float
    
    def to_dict(self) -> dict:
        return {
            'process_id': self.process_id,
            'total_targets': self.total_targets,
            'completed_targets': self.completed_targets,
            'failed_targets': self.failed_targets,
            'active_targets': self.active_targets,
            'total_duration_seconds': self.total_duration_seconds,
            'success_rate': self.success_rate
        }


class MultiTargetProcessor:
    """
    Multi-Target Processor für Parallel Processing
    
    Features:
    - Parallel Processing für 10+ Targets
    - Queue Management
    - Load Balancing
    - Progress Tracking per Target
    - Resource Limiting
    - Retry Logic
    """
    
    def __init__(self, max_concurrent: int = 10, max_retries: int = 3):
        """
        Initialisiere Multi-Target Processor
        
        Args:
            max_concurrent: Maximale gleichzeitige Tasks
            max_retries: Maximale Retry Attempts
        """
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.tasks: Dict[str, TargetTask] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.results: List[MultiTargetResult] = []
        self.task_callback: Optional[Callable] = None
    
    def set_task_callback(self, callback: Callable):
        """
        Setze Task Callback
        
        Args:
            callback: Callback Function (async def callback(task: TargetTask))
        """
        self.task_callback = callback
    
    async def start(self):
        """Starte Multi-Target Processor"""
        self.running = True
        
        # Starte Worker Tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self.workers.append(worker)
        
        logger.info(f"✅ Multi-Target Processor started with {self.max_concurrent} workers")
    
    async def stop(self):
        """Stoppe Multi-Target Processor"""
        self.running = False
        
        # Warte auf alle Workers
        for worker in self.workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Multi-Target Processor stopped")
    
    async def _worker_loop(self, worker_name: str):
        """Worker Loop für Task Processing"""
        while self.running:
            try:
                # Hole Task aus Queue
                task = await self.queue.get()
                
                # Process Task
                await self._process_task(task)
                
                # Markiere Task als fertig
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.info(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)
    
    async def _process_task(self, task: TargetTask):
        """
        Process einzelne Task
        
        Args:
            task: TargetTask
        """
        task.status = TargetStatus.PROCESSING
        task.started_at = datetime.now()
        
        try:
            # Simuliere Processing
            for i in range(10):
                task.progress = i / 10
                await asyncio.sleep(0.5)  # Simuliere Work
            
            # Task Complete
            task.status = TargetStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 1.0
            
            logger.info(f"✅ Task completed: {task.task_id} ({task.victim_address[:10]}...)")
            
            # Trigger Callback
            if self.task_callback:
                await self.task_callback(task)
            
        except Exception as e:
            task.status = TargetStatus.FAILED
            task.error = str(e)
            task.retry_count += 1
            
            logger.info(f"❌ Task failed: {task.task_id} - {e}")
            
            # Retry Logic
            if task.retry_count < self.max_retries:
                task.status = TargetStatus.RETRYING
                await self.queue.put(task)
                logger.info(f"🔄 Retrying task: {task.task_id} (attempt {task.retry_count})")
            else:
                logger.info(f"❌ Task failed permanently: {task.task_id}")
    
    async def submit_task(self, victim_address: str, target_address: str, priority: int = 1) -> str:
        """
        Submit neue Task
        
        Args:
            victim_address: Victim Address
            target_address: Target Address
            priority: Priority (1 = highest)
            
        Returns:
            Task ID
        """
        task_id = f"task_{datetime.now().timestamp()}"
        
        task = TargetTask(
            task_id=task_id,
            victim_address=victim_address,
            target_address=target_address,
            status=TargetStatus.QUEUED,
            priority=priority,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            error=None,
            retry_count=0,
            progress=0.0
        )
        
        self.tasks[task_id] = task
        
        # Füge zur Queue hinzu
        await self.queue.put(task)
        
        logger.info(f"✅ Task submitted: {task_id} ({victim_address[:10]}... → {target_address[:10]}...)")
        
        return task_id
    
    async def submit_batch(self, targets: List[Dict], priority: int = 1) -> List[str]:
        """
        Submit Batch von Tasks
        
        Args:
            targets: Liste von Target Dicts (victim_address, target_address)
            priority: Priority (1 = highest)
            
        Returns:
            Liste von Task IDs
        """
        task_ids = []

        for target in targets:
            victim = target.get('victim_address') or target.get('victim')
            tgt = target.get('target_address') or target.get('target')
            if not victim or not tgt:
                raise ValueError(f"Ungültiger Target-Eintrag: {target} — erwartet victim_address/target_address")
            task_id = await self.submit_task(victim, tgt, priority)
            task_ids.append(task_id)
        
        logger.info(f"✅ Batch submitted: {len(task_ids)} tasks")
        
        return task_ids
    
    def get_task(self, task_id: str) -> Optional[TargetTask]:
        """Hole Task by ID"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TargetTask]:
        """Hole alle Tasks"""
        return list(self.tasks.values())
    
    def get_status(self) -> MultiTargetResult:
        """
        Hole Status für alle Tasks
        
        Returns:
            MultiTargetResult
        """
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == TargetStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TargetStatus.FAILED)
        active = sum(1 for t in self.tasks.values() if t.status == TargetStatus.PROCESSING)
        
        # Berechne Duration
        if self.tasks:
            first_task = min(self.tasks.values(), key=lambda t: t.created_at)
            duration = (datetime.now() - first_task.created_at).total_seconds()
        else:
            duration = 0
        
        success_rate = completed / total if total > 0 else 0
        
        return MultiTargetResult(
            process_id="multi_target_process",
            total_targets=total,
            completed_targets=completed,
            failed_targets=failed,
            active_targets=active,
            total_duration_seconds=duration,
            success_rate=success_rate
        )
    
    async def wait_for_completion(self, timeout_seconds: int = 300):
        """
        Warte auf Completion aller Tasks
        
        Args:
            timeout_seconds: Timeout in Sekunden
        """
        start_time = datetime.now()
        
        while self.running:
            # Prüfe ob alle Tasks fertig
            all_done = all(
                t.status in [TargetStatus.COMPLETED, TargetStatus.FAILED]
                for t in self.tasks.values()
            )
            
            if all_done:
                logger.info(f"✅ All tasks completed")
                break
            
            # Check Timeout
            if (datetime.now() - start_time).total_seconds() > timeout_seconds:
                logger.info(f"⚠️  Timeout reached")
                break
            
            await asyncio.sleep(1)


# Beispiel-Usage
async def main():
    # Erstelle Multi-Target Processor
    processor = MultiTargetProcessor(max_concurrent=10, max_retries=3)
    
    # Starte Processor
    await processor.start()
    
    # Submit Tasks
    targets = [
        {'victim_address': f"0x{i:040x}", 'target_address': f"0x{i+1:040x}"}
        for i in range(20)
    ]
    
    task_ids = await processor.submit_batch(targets)
    logger.info(f"✅ Submitted {len(task_ids)} tasks")
    
    # Warte auf Completion
    await processor.wait_for_completion(timeout_seconds=60)
    
    # Hole Status
    status = processor.get_status()
    logger.info(f"\n✅ Status:")
    logger.info(f"   Total: {status.total_targets}")
    logger.info(f"   Completed: {status.completed_targets}")
    logger.info(f"   Failed: {status.failed_targets}")
    logger.info(f"   Active: {status.active_targets}")
    logger.info(f"   Success Rate: {status.success_rate:.2%}")
    logger.info(f"   Duration: {status.total_duration_seconds:.2f}s")
    
    # Stoppe Processor
    await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())