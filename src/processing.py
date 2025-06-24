import asyncio
import logging
import multiprocessing as mp
import queue
import threading
import time
import uuid
from typing import Dict, List, Optional

# Handle both relative and absolute imports
try:
    from .config import (ENABLE_PROMPT_BATCHING, MAX_BATCH_SIZE, MAX_TOTAL_PIXELS,
                        NUM_WORKER_PROCESSES, BATCH_TIMEOUT)
    from .schemas import BatchedGenerationRequest, GenerationRequest
    from .utils import display_ready_banner
    from .worker import worker_process
except ImportError:
    from config import (ENABLE_PROMPT_BATCHING, MAX_BATCH_SIZE, MAX_TOTAL_PIXELS,
                        NUM_WORKER_PROCESSES, BATCH_TIMEOUT)
    from schemas import BatchedGenerationRequest, GenerationRequest
    from utils import display_ready_banner
    from worker import worker_process

logger = logging.getLogger(__name__)


class BatchManager:
    """Manages batching of compatible requests"""

    def __init__(self, batch_timeout: float = BATCH_TIMEOUT, max_batch_size: int = MAX_BATCH_SIZE):
        self.batch_timeout = batch_timeout
        self.max_batch_size = max_batch_size
        self.pending_requests: Dict[tuple, List[GenerationRequest]] = {}
        self.batch_timers: Dict[tuple, float] = {}
        self.lock = threading.Lock()

    def get_batch_key(self, request: GenerationRequest) -> tuple:
        """Generate a key for batching compatible requests"""
        return (
            request.width, request.height, request.guidance_scale,
            request.num_inference_steps, request.stream, request.num_images,
            request.seed
        )

    def add_request(self, request: GenerationRequest) -> Optional[BatchedGenerationRequest]:
        """Add a request and return a batch if ready"""
        with self.lock:
            batch_key = self.get_batch_key(request)

            if batch_key not in self.pending_requests:
                self.pending_requests[batch_key] = []
                self.batch_timers[batch_key] = time.time()

            current_batch = self.pending_requests[batch_key]
            pixels_per_request = request.width * request.height * request.num_images
            total_pixels = pixels_per_request * (len(current_batch) + 1)

            if total_pixels >= MAX_TOTAL_PIXELS and current_batch:
                batch = self._create_batch(batch_key, current_batch)
                self.pending_requests[batch_key] = [request]
                self.batch_timers[batch_key] = time.time()
                logger.debug(f"BatchManager: Flushed batch due to VRAM limit ({total_pixels:,} > {MAX_TOTAL_PIXELS:,})")
                return batch

            self.pending_requests[batch_key].append(request)
            batch_requests = self.pending_requests[batch_key]
            time_elapsed = time.time() - self.batch_timers[batch_key]

            if len(batch_requests) >= self.max_batch_size or time_elapsed >= self.batch_timeout:
                batch = self._create_batch(batch_key, batch_requests)
                del self.pending_requests[batch_key]
                del self.batch_timers[batch_key]
                return batch

            return None

    def flush_pending_batches(self) -> List[BatchedGenerationRequest]:
        """Flush all pending batches"""
        with self.lock:
            batches = [self._create_batch(k, v) for k, v in self.pending_requests.items() if v]
            self.pending_requests.clear()
            self.batch_timers.clear()
            return batches

    def check_timeouts(self) -> List[BatchedGenerationRequest]:
        """Check for timed out batches"""
        with self.lock:
            expired_keys = [k for k, v in self.batch_timers.items() if time.time() - v >= self.batch_timeout]
            batches = []
            for key in expired_keys:
                batch_requests = self.pending_requests.pop(key, [])
                if batch_requests:
                    batches.append(self._create_batch(key, batch_requests))
                self.batch_timers.pop(key, None)
            return batches

    def _create_batch(self, batch_key: tuple, requests: List[GenerationRequest]) -> BatchedGenerationRequest:
        """Create a batched request from individual requests"""
        first = requests[0]
        return BatchedGenerationRequest(
            batch_id=str(uuid.uuid4())[:8],
            prompts=[r.prompt for r in requests],
            negative_prompts=[r.negative_prompt for r in requests],
            request_ids=[r.request_id for r in requests],
            num_images=first.num_images, width=first.width, height=first.height,
            guidance_scale=first.guidance_scale, num_inference_steps=first.num_inference_steps,
            stream=first.stream,
            seeds=[r.seed for r in requests]
        )


class WorkerPool:
    """Manages a pool of persistent worker processes"""

    def __init__(self, model_path: str, num_workers: int = NUM_WORKER_PROCESSES):
        self.model_path = model_path
        self.num_workers = num_workers
        try:
            mp.set_start_method('spawn', force=True)
            logger.info("Set multiprocessing start method to 'spawn'")
        except RuntimeError:
            logger.warning(f"Multiprocessing start method already set to: {mp.get_start_method()}")

        self.mp_context = mp.get_context('spawn')
        self.manager = self.mp_context.Manager()
        self.request_queue = self.manager.Queue()
        self.result_queue = self.manager.Queue()
        self.shutdown_event = self.mp_context.Event()
        self.worker_model_loaded = self.manager.dict()
        self.workers = []
        self.active_requests = {}
        self.lock = threading.Lock()

        logger.info(f"Initializing worker pool with {num_workers} workers")
        for i in range(num_workers):
            self.worker_model_loaded[i] = False
            worker = self.mp_context.Process(
                target=worker_process,
                args=(i, model_path, self.request_queue, self.result_queue, self.shutdown_event, self.worker_model_loaded)
            )
            worker.start()
            self.workers.append(worker)
        logger.info(f"Worker pool initialized with {len(self.workers)} workers")

        self.batch_manager = BatchManager()
        self.batch_enabled = ENABLE_PROMPT_BATCHING
        if self.batch_enabled:
            self.batch_thread = threading.Thread(target=self._batch_timeout_checker, daemon=True)
            self.batch_thread.start()
            logger.info("Prompt batching enabled - timeout checker started")
        else:
            logger.info("Prompt batching disabled")

        self.ready_banner_shown = False
        self.readiness_thread = threading.Thread(target=self._monitor_worker_readiness, daemon=True)
        self.readiness_thread.start()
        logger.info("Worker readiness monitor started")

    def _batch_timeout_checker(self):
        while not self.shutdown_event.is_set():
            try:
                expired_batches = self.batch_manager.check_timeouts()
                for batch in expired_batches:
                    self.request_queue.put(batch)
                    logger.debug(f"Submitted timed-out batch {batch.batch_id} with {len(batch.prompts)} prompts")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in batch timeout checker: {e}")
                time.sleep(1.0)

    def all_models_loaded(self) -> bool:
        if not self.worker_model_loaded: return False
        loaded_workers = sum(1 for loaded in self.worker_model_loaded.values() if loaded)
        logger.debug(f"Model loading status: {loaded_workers}/{self.num_workers} workers have loaded models")
        return loaded_workers == self.num_workers and self.num_workers > 0

    def is_ready(self) -> bool:
        return self.all_models_loaded() and self.ready_banner_shown

    async def submit_request(self, stream: bool, **kwargs):
        request_id = str(uuid.uuid4())[:8]
        gen_request = GenerationRequest(request_id=request_id, stream=stream, **kwargs)

        with self.lock:
            self.active_requests[request_id] = True

        if self.batch_enabled:
            batch = self.batch_manager.add_request(gen_request)
            if batch:
                self.request_queue.put(batch)
                logger.info(f"Submitted batch {batch.batch_id} with {len(batch.prompts)} prompts (including {request_id})")
            else:
                logger.debug(f"Added request {request_id} to pending batch (stream={stream})")
        else:
            self.request_queue.put(gen_request)
            logger.info(f"Submitted individual request {request_id} (stream={stream})")

        try:
            if stream:
                async for result in self._stream_results(request_id):
                    yield result
            else:
                result = await self._wait_for_completion(request_id)
                yield result
        finally:
            with self.lock:
                self.active_requests.pop(request_id, None)

    async def submit_non_streaming_request(self, **kwargs):
        """Submit a non-streaming request and return the result directly"""
        request_id = str(uuid.uuid4())[:8]
        gen_request = GenerationRequest(request_id=request_id, stream=False, **kwargs)

        with self.lock:
            self.active_requests[request_id] = True

        if self.batch_enabled:
            batch = self.batch_manager.add_request(gen_request)
            if batch:
                self.request_queue.put(batch)
                logger.info(f"Submitted batch {batch.batch_id} with {len(batch.prompts)} prompts (including {request_id})")
            else:
                logger.debug(f"Added request {request_id} to pending batch (stream=False)")
        else:
            self.request_queue.put(gen_request)
            logger.info(f"Submitted individual request {request_id} (stream=False)")

        try:
            return await self._wait_for_completion(request_id)
        finally:
            with self.lock:
                self.active_requests.pop(request_id, None)

    async def _stream_results(self, request_id: str):
        while True:
            try:
                result = self.result_queue.get(timeout=0.1)
                if result.request_id != request_id:
                    self.result_queue.put(result)
                    await asyncio.sleep(0.01)
                    continue
                if result.result_type == 'error':
                    raise Exception(result.data['error'])
                if result.result_type == 'completed':
                    break
                if result.result_type == 'streaming_step':
                    yield result.data
            except queue.Empty:
                await asyncio.sleep(0.05)

    async def _wait_for_completion(self, request_id: str):
        while True:
            try:
                result = self.result_queue.get(timeout=0.1)
                if result.request_id != request_id:
                    self.result_queue.put(result)
                    await asyncio.sleep(0.01)
                    continue
                if result.result_type == 'error':
                    raise Exception(result.data['error'])
                if result.result_type == 'completed':
                    return result.data
            except queue.Empty:
                await asyncio.sleep(0.05)

    def shutdown(self):
        logger.info("Shutting down worker pool...")
        if self.batch_enabled:
            pending_batches = self.batch_manager.flush_pending_batches()
            for batch in pending_batches:
                self.request_queue.put(batch)
                logger.info(f"Flushed pending batch {batch.batch_id} with {len(batch.prompts)} prompts")
        self.shutdown_event.set()
        for i, worker in enumerate(self.workers):
            worker.join(timeout=10)
            if worker.is_alive():
                logger.warning(f"Force terminating worker {i}")
                worker.terminate()
                worker.join()
        logger.info("Worker pool shutdown complete")

    def _monitor_worker_readiness(self):
        logger.info("Starting worker readiness monitoring...")
        last_logged_count = 0
        while not self.shutdown_event.is_set() and not self.ready_banner_shown:
            try:
                if self.all_models_loaded():
                    if not self.ready_banner_shown:
                        self.ready_banner_shown = True
                        logger.info("All workers have loaded models - displaying ready banner")
                        display_ready_banner()
                    break
                else:
                    loaded_count = sum(1 for loaded in self.worker_model_loaded.values() if loaded)
                    if loaded_count != last_logged_count and loaded_count > 0:
                        logger.info(f"Worker loading progress: {loaded_count}/{self.num_workers} workers ready")
                        last_logged_count = loaded_count
                time.sleep(2.0)
            except Exception as e:
                logger.error(f"Error in readiness monitor: {e}")
                time.sleep(5.0)
        logger.debug("Worker readiness monitoring thread exiting") 