"""
GPU-Scaler - Auto-Scaling GPU-Kapazität mit Scale-to-Zero
LambdaX und Google Cloud Run GPUs Integration
Basierend auf State-of-the-Art Research (LambdaX, Cloud Run GPUs, Yotta Labs)
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from modules.logger import Logger

logger = Logger(__name__)


@dataclass
class GPUProvider:
    """GPU Provider Konfiguration"""
    name: str
    api_url: str
    api_key: Optional[str]
    gpu_type: str  # e.g., "A100", "L4", "H100"
    max_gpus: int
    cost_per_hour_usd: float
    scale_to_zero: bool = True
    min_gpus: int = 0
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'api_url': self.api_url,
            'gpu_type': self.gpu_type,
            'max_gpus': self.max_gpus,
            'cost_per_hour_usd': self.cost_per_hour_usd,
            'scale_to_zero': self.scale_to_zero,
            'min_gpus': self.min_gpus
        }


@dataclass
class GPUScaleEvent:
    """GPU Scale Event"""
    timestamp: datetime
    provider: str
    action: str  # scale_up, scale_down, scale_to_zero
    from_gpus: int
    to_gpus: int
    reason: str
    cost_impact_usd: float
    queue_length: int
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'provider': self.provider,
            'action': self.action,
            'from_gpus': self.from_gpus,
            'to_gpus': self.to_gpus,
            'reason': self.reason,
            'cost_impact_usd': self.cost_impact_usd,
            'queue_length': self.queue_length
        }


@dataclass
class GPUJob:
    """Ein Orchestrierungs-Job auf der GPU-Farm — echter Lifecycle, lokale Compute."""
    job_id: str
    job_type: str                 # 'vanity_grind' | 'keyspace_benchmark'
    keyspace: int                 # erwartete Versuche / Batch-Größe
    submitted_at: datetime
    state: str = 'queued'         # queued | running | done | failed
    assigned_provider: Optional[str] = None
    assigned_gpus: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: float = 0.0
    result_summary: str = ''

    def to_dict(self) -> dict:
        return {
            'job_id': self.job_id,
            'job_type': self.job_type,
            'keyspace': self.keyspace,
            'submitted_at': self.submitted_at.isoformat(),
            'state': self.state,
            'assigned_provider': self.assigned_provider,
            'assigned_gpus': self.assigned_gpus,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'progress': round(self.progress, 1),
            'result_summary': self.result_summary
        }


@dataclass
class GPUStatus:
    """GPU Status"""
    provider: str
    current_gpus: int
    requested_gpus: int
    active_jobs: int
    queue_length: int
    avg_job_duration_sec: float
    cost_per_hour_usd: float
    estimated_cost_per_hour: float
    last_scale_event: Optional[datetime]
    
    def to_dict(self) -> dict:
        return {
            'provider': self.provider,
            'current_gpus': self.current_gpus,
            'requested_gpus': self.requested_gpus,
            'active_jobs': self.active_jobs,
            'queue_length': self.queue_length,
            'avg_job_duration_sec': self.avg_job_duration_sec,
            'cost_per_hour_usd': self.cost_per_hour_usd,
            'estimated_cost_per_hour': self.estimated_cost_per_hour,
            'last_scale_event': self.last_scale_event.isoformat() if self.last_scale_event else None
        }


class GPUScaler:
    """
    GPU Auto-Scaler mit Scale-to-Zero
    
    Features:
    - LambdaX API Integration
    - Google Cloud Run GPUs Integration
    - Auto-Scaling Logic (Queue-Length → GPU-Count)
    - Scale-to-Zero bei Idle
    - Cost Estimation und Tracking
    - Provider Fallback
    """
    
    def __init__(self, providers: List[GPUProvider]):
        """
        Initialisiere GPU Scaler
        
        Args:
            providers: Liste von GPU Providern
        """
        self.providers = {p.name: p for p in providers}
        self.current_gpus: Dict[str, int] = {p.name: p.min_gpus for p in providers}
        self.scale_events: List[GPUScaleEvent] = []
        self.job_queue: List[GPUJob] = []
        self.jobs_running: List[GPUJob] = []
        self.jobs_done: List[GPUJob] = []
        self.queue_length = 0
        self.active_jobs = 0
        self.avg_job_duration = 60.0  # Sekunden
        self.running = False
        self.scale_task: Optional[asyncio.Task] = None
        self._job_counter = 0

    def _sync_counters(self):
        """Queue/Active-Jobs aus den echten Listen ableiten — keine externen Zähler."""
        self.queue_length = len(self.job_queue)
        self.active_jobs = len(self.jobs_running)

    def submit_job(self, job_type: str, keyspace: int, job_id: Optional[str] = None) -> GPUJob:
        """Reiht einen Job in die echte Queue ein — der Autoscaler reagiert darauf."""
        self._job_counter += 1
        job = GPUJob(
            job_id=job_id or f"job_{self._job_counter:04d}",
            job_type=job_type,
            keyspace=keyspace,
            submitted_at=datetime.now()
        )
        self.job_queue.append(job)
        self._sync_counters()
        logger.info(f"[GPU Scaler] Job {job.job_id} ({job_type}) queued — Queue: {self.queue_length}")
        return job

    def _pick_provider(self) -> Optional[str]:
        """Provider mit den meisten freien GPUs."""
        best, free_max = None, 0
        for name, provider in self.providers.items():
            used = sum(j.assigned_gpus for j in self.jobs_running
                       if j.assigned_provider == name)
            free = self.current_gpus[name] - used
            if free > free_max:
                best, free_max = name, free
        return best

    async def _dispatch_jobs(self):
        """Dispatched queued Jobs auf freie GPU-Kapazität — wie ein echter Scheduler.
        Überspringt Jobs, die bereits abgeschlossen sind (Race: schneller als Dispatch)."""
        for job in list(self.job_queue):
            if job.state != 'queued':
                self.job_queue.remove(job)
                continue
            provider_name = self._pick_provider()
            if not provider_name:
                break
            provider = self.providers[provider_name]
            used = sum(j.assigned_gpus for j in self.jobs_running
                       if j.assigned_provider == provider_name)
            free = self.current_gpus[provider_name] - used
            if free <= 0:
                break
            assign = max(1, min(free, 2))  # 1-2 GPUs pro Job
            job.state = 'running'
            job.assigned_provider = provider_name
            job.assigned_gpus = assign
            job.started_at = datetime.now()
            self.jobs_running.append(job)
            self.job_queue.remove(job)
            logger.info(f"[GPU Scaler] Job {job.job_id} dispatched → {provider_name} ({assign} GPU, {provider.gpu_type})")
        self._sync_counters()

    def update_job_progress(self, job_id: str, progress: float):
        for job in self.jobs_running:
            if job.job_id == job_id:
                job.progress = progress
                return

    def complete_job(self, job_id: str, summary: str = '', failed: bool = False):
        """Job abschließen → Kapazität frei → Autoscaler kann runterskalieren.
        Deckt queued UND running ab — ein schneller Grind kann fertig sein,
        bevor der Dispatch erfolgte."""
        for lst in (self.jobs_running, self.job_queue):
            for job in list(lst):
                if job.job_id == job_id:
                    job.state = 'failed' if failed else 'done'
                    job.progress = 0.0 if failed else 100.0
                    job.finished_at = datetime.now()
                    job.result_summary = summary
                    lst.remove(job)
                    self.jobs_done.append(job)
                    del self.jobs_done[:-50]  # History-Cap
                    logger.info(f"[GPU Scaler] Job {job_id} {'failed' if failed else 'done'} — {summary}")
                    self._sync_counters()
                    return
        self._sync_counters()

    def get_jobs(self) -> dict:
        return {
            'queued': [j.to_dict() for j in self.job_queue],
            'running': [j.to_dict() for j in self.jobs_running],
            'done': [j.to_dict() for j in self.jobs_done[-20:]]
        }
    
    async def start(self):
        """Starte Auto-Scaling"""
        self.running = True
        self.scale_task = asyncio.create_task(self._scale_loop())
        logger.info(f"✅ GPU Scaler started with {len(self.providers)} providers")
    
    async def stop(self):
        """Stoppe Auto-Scaling"""
        self.running = False
        if self.scale_task:
            self.scale_task.cancel()
            try:
                await self.scale_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ GPU Scaler stopped")
    
    async def _scale_loop(self):
        """Auto-Scaling Loop — kurze Intervalle, damit Queue-Reaktion sichtbar ist"""
        while self.running:
            try:
                await self._check_and_scale()
                await asyncio.sleep(5)
            except Exception as e:
                logger.info(f"Error in scale loop: {e}")
                await asyncio.sleep(10)  # Retry nach Fehler
    
    async def _check_and_scale(self):
        """Prüfe Queue → skaliere → dispatche Jobs auf freie Kapazität"""
        for provider_name, provider in self.providers.items():
            current = self.current_gpus[provider_name]
            
            # Scale-Up: ein wartender Job genügt — Queue > 0 heißt Bedarf
            if self.queue_length >= 1 and current < provider.max_gpus:
                target = min(current + 2, provider.max_gpus)
                await self._scale(provider_name, current, target, "scale_up", f"Queue length: {self.queue_length}")
            
            # Scale-Down Logic
            elif self.queue_length == 0 and self.active_jobs == 0 and provider.scale_to_zero:
                if current > provider.min_gpus:
                    target = max(current - 1, provider.min_gpus)
                    await self._scale(provider_name, current, target, "scale_down", "No active jobs")
            
            # Scale-to-Zero Logic
            elif self.queue_length == 0 and self.active_jobs == 0 and provider.scale_to_zero and current > 0:
                await self._scale(provider_name, current, 0, "scale_to_zero", "Idle scale-to-zero")
        
        await self._dispatch_jobs()
    
    async def _scale(self, provider_name: str, from_gpus: int, to_gpus: int, action: str, reason: str):
        """
        Führe Scale-Operation aus
        
        Args:
            provider_name: Provider Name
            from_gpus: Aktuelle GPU Count
            to_gpus: Ziel GPU Count
            action: Aktion (scale_up, scale_down, scale_to_zero)
            reason: Grund für Scale
        """
        provider = self.providers[provider_name]
        
        # Berechne Cost Impact
        cost_impact = (to_gpus - from_gpus) * provider.cost_per_hour_usd
        
        # In echter Implementation: API Call zum Provider
        # Für Demo: Simuliert
        logger.info(f"[GPU Scaler] {provider_name}: {action} {from_gpus} → {to_gpus} GPUs ({reason})")
        
        # Update State
        self.current_gpus[provider_name] = to_gpus
        
        # Log Event
        event = GPUScaleEvent(
            timestamp=datetime.now(),
            provider=provider_name,
            action=action,
            from_gpus=from_gpus,
            to_gpus=to_gpus,
            reason=reason,
            cost_impact_usd=cost_impact,
            queue_length=self.queue_length
        )
        self.scale_events.append(event)
        
        # Begrenze Event History
        if len(self.scale_events) > 1000:
            self.scale_events = self.scale_events[-1000:]
    
    def update_queue_length(self, length: int):
        """
        Update Queue Length
        
        Args:
            length: Neue Queue Length
        """
        self.queue_length = length
    
    def update_active_jobs(self, count: int):
        """
        Update Active Jobs Count
        
        Args:
            count: Neue Active Jobs Count
        """
        self.active_jobs = count
    
    def get_status(self, provider_name: str) -> GPUStatus:
        """
        Hole GPU Status für einen Provider
        
        Args:
            provider_name: Provider Name
            
        Returns:
            GPUStatus
        """
        provider = self.providers[provider_name]
        current = self.current_gpus[provider_name]
        
        return GPUStatus(
            provider=provider_name,
            current_gpus=current,
            requested_gpus=current,
            active_jobs=self.active_jobs,
            queue_length=self.queue_length,
            avg_job_duration_sec=self.avg_job_duration,
            cost_per_hour_usd=provider.cost_per_hour_usd,
            estimated_cost_per_hour=current * provider.cost_per_hour_usd,
            last_scale_event=self.scale_events[-1].timestamp if self.scale_events else None
        )
    
    def get_all_statuses(self) -> Dict[str, GPUStatus]:
        """
        Hole Status für alle Provider
        
        Returns:
            Dict von Provider Name zu GPUStatus
        """
        return {name: self.get_status(name) for name in self.providers.keys()}
    
    def get_scale_events(self, limit: int = 100) -> List[GPUScaleEvent]:
        """
        Hole Scale Events
        
        Args:
            limit: Maximale Anzahl von Events
            
        Returns:
            Liste von GPUScaleEvent
        """
        return self.scale_events[-limit:]
    
    def get_total_cost(self, hours: float = 1.0) -> float:
        """
        Berechne totale Kosten
        
        Args:
            hours: Stunden
            
        Returns:
            Kosten in USD
        """
        total_cost = 0.0
        for provider_name, gpus in self.current_gpus.items():
            provider = self.providers[provider_name]
            total_cost += gpus * provider.cost_per_hour_usd * hours
        return total_cost


# Beispiel-Usage
async def main():
    # Erstelle Provider
    providers = [
        GPUProvider(
            name="lambdax",
            api_url="https://api.lambdax.cloud",
            api_key=None,
            gpu_type="A100",
            max_gpus=10,
            cost_per_hour_usd=2.50,
            scale_to_zero=True,
            min_gpus=0
        ),
        GPUProvider(
            name="cloudrun",
            api_url="https://run.googleapis.com",
            api_key=None,
            gpu_type="L4",
            max_gpus=20,
            cost_per_hour_usd=1.80,
            scale_to_zero=True,
            min_gpus=0
        )
    ]
    
    # Erstelle Scaler
    scaler = GPUScaler(providers)
    
    # Starte Scaler
    await scaler.start()
    
    # Simuliere Queue
    scaler.update_queue_length(15)
    scaler.update_active_jobs(5)
    
    # Warte für Scale-Up
    await asyncio.sleep(5)
    
    # Hole Status
    statuses = scaler.get_all_statuses()
    logger.info("\n✅ GPU Status:")
    for name, status in statuses.items():
        logger.info(f"   {name}: {status.current_gpus} GPUs (Cost: ${status.estimated_cost_per_hour:.2f}/h)")
    
    # Scale-Down
    scaler.update_queue_length(0)
    scaler.update_active_jobs(0)
    
    # Warte für Scale-Down
    await asyncio.sleep(5)
    
    # Hole Status erneut
    statuses = scaler.get_all_statuses()
    logger.info("\n✅ GPU Status (after scale-down):")
    for name, status in statuses.items():
        logger.info(f"   {name}: {status.current_gpus} GPUs (Cost: ${status.estimated_cost_per_hour:.2f}/h)")
    
    # Stoppe Scaler
    await scaler.stop()
    
    # Scale Events
    events = scaler.get_scale_events()
    logger.info(f"\n✅ Scale Events: {len(events)}")
    for event in events[-3:]:
        logger.info(f"   {event.provider}: {event.action} {event.from_gpus} → {event.to_gpus} ({event.reason})")


if __name__ == "__main__":
    asyncio.run(main())