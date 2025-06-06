#!/usr/bin/env python3
"""
CogView4 Image Generation API Server with SSE Streaming
Implements OpenAI-compatible image generation API with streaming intermediate results
"""

import asyncio
import base64
import io
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List
import multiprocessing as mp
import queue
import threading
from dataclasses import dataclass

import torch
from PIL import Image
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from torchao.quantization import int8_weight_only, quantize_

# Import CogView4 components
from diffusers import CogView4Pipeline
from transformers import GlmModel
from diffusers import CogView4Transformer2DModel

# Configure logging at module level
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_file = os.getenv('LOG_FILE', 'cogview4_api.log')

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ],
    force=True
)

logger = logging.getLogger(__name__)
NUM_WORKER_PROCESSES = int(os.getenv('NUM_WORKER_PROCESSES', '4'))

logger.info(f"Starting CogView4 API with log level: {log_level}")
logger.info(f"Log file: {log_file}")
logger.info(f"Number of worker processes: {NUM_WORKER_PROCESSES}")

@dataclass
class GenerationRequest:
    """Request data structure for worker processes"""
    request_id: str
    prompt: str
    negative_prompt: Optional[str]
    width: int
    height: int
    guidance_scale: float
    num_inference_steps: int
    num_images: int
    stream: bool

@dataclass
class GenerationResult:
    """Result data structure from worker processes"""
    request_id: str
    result_type: str  # 'streaming_step', 'completed', 'error'
    data: Any = None

class ImageGenerationRequest(BaseModel):
    """OpenAI-compatible image generation request"""
    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt to avoid certain elements")
    n: int = Field(1, description="Number of images to generate", ge=1, le=4)
    size: str = Field("1024x1024", description="Image size (width x height)")
    quality: str = Field("standard", description="Image quality")
    style: str = Field("natural", description="Image style")
    response_format: str = Field("b64_json", description="Response format")
    user: Optional[str] = Field(None, description="User identifier")
    stream: bool = Field(False, description="Whether to stream intermediate results")
    guidance_scale: float = Field(5.0, description="Guidance scale for generation", ge=1.0, le=20.0)
    num_inference_steps: int = Field(50, description="Number of inference steps", ge=10, le=150)


class ImageData(BaseModel):
    """Image data response"""
    b64_json: Optional[str] = None
    url: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """OpenAI-compatible image generation response"""
    created: int
    data: List[ImageData]


class StreamingImageData(BaseModel):
    """Streaming image data for SSE"""
    step: int
    total_steps: int
    progress: float
    image: Optional[str] = None  # base64 encoded image
    timestamp: float
    is_final: bool = False
    # Chunking support
    is_chunked: bool = False
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None


def _parse_size(size_str: str) -> tuple:
    """Parse size string like '1024x1024' to (width, height)"""
    try:
        width, height = map(int, size_str.split('x'))
        return width, height
    except:
        return 1024, 1024  # Default size


def worker_process(worker_id: int, model_path: str, request_queue: mp.Queue, result_queue: mp.Queue, shutdown_event: mp.Event, worker_model_loaded: Dict[int, bool]):
    """
    Persistent worker process that loads the model once and handles multiple requests.
    Each worker can handle one request at a time but can use from_pipe for concurrent sub-requests.
    """
    import logging
    import torch
    from diffusers import CogView4Pipeline
    import time
    import base64
    import io
    from PIL import Image
    import os
    
    # Set up logging for this worker
    worker_logger = logging.getLogger(f"worker_{worker_id}")
    worker_logger.info(f"Worker {worker_id} starting up...")
    
    # Set up logging for this worker process (spawn doesn't inherit main process logging)
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'cogview4_api.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=f'%(asctime)s - Worker{worker_id} - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ],
        force=True  # Override any existing configuration
    )
    
    # Import quantization modules needed for model loading
    from torchao.quantization import int8_weight_only, quantize_
    from transformers import GlmModel
    from diffusers import CogView4Transformer2DModel
    
    # Re-initialize worker logger with proper configuration
    worker_logger = logging.getLogger(f"worker_{worker_id}")
    worker_logger.info(f"Worker {worker_id} starting up with proper logging configured...")
    
    # Add delay between worker startups to avoid CUDA initialization conflicts
    time.sleep(worker_id * 3.0)  # Increased delay for better CUDA handling
    
    # Set CUDA environment variables for this process
    os.environ['CUDA_LAUNCH_BLOCKING'] = '1'  # For better error reporting
    os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
    
    # Only proceed if CUDA is available
    if not torch.cuda.is_available():
        worker_logger.error(f"Worker {worker_id}: CUDA not available. This worker will exit.")
        return
    
    # Load the base pipeline once per worker
    try:
        # Initialize CUDA properly for this worker
        try:
            # Explicit CUDA initialization
            torch.cuda.init()
            
            # Determine which GPU to use (distribute workers across available GPUs)
            num_gpus = torch.cuda.device_count()
            gpu_id = worker_id % num_gpus  # Distribute workers across available GPUs
            device = f"cuda:{gpu_id}"
            
            worker_logger.info(f"Worker {worker_id}: Using {device} (GPU {gpu_id} of {num_gpus} available)")
            
            # Set the current device
            torch.cuda.set_device(gpu_id)
            torch.cuda.empty_cache()
            
            # Test CUDA access on the assigned device
            with torch.cuda.device(gpu_id):
                test_tensor = torch.tensor([1.0], device=device)
                test_result = test_tensor + 1
                del test_tensor, test_result
                torch.cuda.empty_cache()
            
            worker_logger.info(f"Worker {worker_id}: CUDA device {gpu_id} initialized successfully")
            
        except Exception as cuda_error:
            worker_logger.error(f"Worker {worker_id}: CUDA initialization failed: {cuda_error}")
            worker_logger.error(f"Worker {worker_id}: Cannot proceed without CUDA. Exiting.")
            return
        
        # Load base pipeline on the assigned GPU
        try:
            worker_logger.info(f"Worker {worker_id}: Loading model on {device}...")
            text_encoder = GlmModel.from_pretrained(model_path, subfolder="text_encoder", torch_dtype=torch.bfloat16)
            transformer = CogView4Transformer2DModel.from_pretrained(model_path, subfolder="transformer", torch_dtype=torch.bfloat16)
            quantize_(text_encoder, int8_weight_only())
            quantize_(transformer, int8_weight_only())
            base_pipeline = CogView4Pipeline.from_pretrained(
                model_path,
                text_encoder=text_encoder,
                transformer=transformer,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True
            )
            
            # Move pipeline to the assigned device
            base_pipeline.to(device)
            
            worker_logger.info(f"Worker {worker_id}: Successfully loaded base pipeline on {device}")
            
            # Report model loading success to shared state
            worker_model_loaded[worker_id] = True
            worker_logger.info(f"Worker {worker_id}: Model loading status updated to True")
            
        except Exception as model_error:
            worker_logger.error(f"Worker {worker_id}: Failed to load model on {device}: {model_error}")
            worker_logger.error(f"Worker {worker_id}: Cannot proceed without model. Exiting.")
            # Ensure model loading status remains False on failure
            worker_model_loaded[worker_id] = False
            return
        
        # Dictionary to store active pipeline instances for concurrent requests
        active_pipelines = {}
        
        def get_pipeline_for_request(request_id: str):
            """Get or create a pipeline instance using from_pipe for memory efficiency"""
            if request_id not in active_pipelines:
                try:
                    # Use from_pipe to create efficient pipeline instance
                    with torch.cuda.device(gpu_id):
                        pipeline = CogView4Pipeline.from_pipe(base_pipeline)
                        pipeline.set_progress_bar_config(disable=False, desc=f"Worker {worker_id}")
                        # Create separate scheduler to avoid state conflicts
                        base_scheduler = base_pipeline.scheduler
                        scheduler_class = base_scheduler.__class__
                        scheduler_config = base_scheduler.config
                        new_scheduler = scheduler_class.from_config(scheduler_config)
                        pipeline.scheduler = new_scheduler
                        
                        active_pipelines[request_id] = pipeline
                        worker_logger.debug(f"Worker {worker_id}: Created pipeline instance for request {request_id} on {device}")
                    
                except Exception as pipe_error:
                    worker_logger.error(f"Worker {worker_id}: Failed to create pipeline for request {request_id}: {pipe_error}")
                    raise
            
            return active_pipelines[request_id]
        
        def cleanup_pipeline(request_id: str):
            """Clean up pipeline instance after request completion"""
            if request_id in active_pipelines:
                try:
                    with torch.cuda.device(gpu_id):
                        del active_pipelines[request_id]
                        # torch.cuda.empty_cache()
                    worker_logger.debug(f"Worker {worker_id}: Cleaned up pipeline for request {request_id}")
                except Exception as cleanup_error:
                    worker_logger.warning(f"Worker {worker_id}: Error during cleanup: {cleanup_error}")
        
        def send_chunked_image(image_b64: str, step_index: int, is_final_step: bool, max_chunk_size: int = 400 * 1024):
            """Send large image data in chunks via multiple SSE events"""
            if len(image_b64) <= max_chunk_size:
                # Small enough to send in one piece
                result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='streaming_step',
                    data={
                        'step': step_index,
                        'progress': (step_index + 1) / gen_request.num_inference_steps,
                        'image': image_b64,
                        'is_final': is_final_step,
                        'timestamp': time.time(),
                        'is_chunked': False
                    }
                )
                result_queue.put(result)
                worker_logger.debug(f"Worker {worker_id}: Sent single image for step {step_index}")
            else:
                # Need to chunk the image
                chunk_id = f"{gen_request.request_id}_step_{step_index}_{int(time.time() * 1000)}"
                total_chunks = (len(image_b64) + max_chunk_size - 1) // max_chunk_size
                
                worker_logger.debug(f"Worker {worker_id}: Chunking image for step {step_index} into {total_chunks} chunks")
                
                for chunk_index in range(total_chunks):
                    start_pos = chunk_index * max_chunk_size
                    end_pos = min(start_pos + max_chunk_size, len(image_b64))
                    chunk_data = image_b64[start_pos:end_pos]
                    
                    result = GenerationResult(
                        request_id=gen_request.request_id,
                        result_type='streaming_step',
                        data={
                            'step': step_index,
                            'progress': (step_index + 1) / gen_request.num_inference_steps,
                            'image': chunk_data,
                            'is_final': is_final_step,
                            'timestamp': time.time(),
                            'is_chunked': True,
                            'chunk_id': chunk_id,
                            'chunk_index': chunk_index,
                            'total_chunks': total_chunks
                        }
                    )
                    result_queue.put(result)
                    
                worker_logger.debug(f"Worker {worker_id}: Sent {total_chunks} chunks for step {step_index}")

        def step_callback(pipeline_instance, step_index, timestep, callback_kwargs):
            """Callback function that runs for each denoising step"""
            try:
                # Get current latents
                latents = callback_kwargs.get("latents")
                if latents is not None:
                    # Decode latents to image for every step
                    with torch.no_grad():
                        try:
                            with torch.cuda.device(gpu_id):
                                # Decode latents to image
                                latents_for_decode = latents.to(pipeline_instance.vae.dtype) / pipeline_instance.vae.config.scaling_factor
                                decoded_image = pipeline_instance.vae.decode(latents_for_decode, return_dict=False)[0]
                                
                                # Post-process
                                decoded_image = pipeline_instance.image_processor.postprocess(decoded_image, output_type="pil")
                                
                                if isinstance(decoded_image, list) and len(decoded_image) > 0:
                                    image = decoded_image[0]
                                    is_final_step = step_index == gen_request.num_inference_steps - 1
                                    
                                    # Keep full resolution - no resizing
                                    # Convert to base64 with appropriate format
                                    buffer = io.BytesIO()
                                    if is_final_step:
                                        # Use PNG for final images (highest quality)
                                        image.save(buffer, format='PNG', optimize=True)
                                    else:
                                        # Use high-quality JPEG for intermediate steps
                                        if image.mode in ('RGBA', 'LA', 'P'):
                                            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                                            if image.mode == 'P':
                                                image = image.convert('RGBA')
                                            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                                            image = rgb_image
                                        image.save(buffer, format='JPEG', quality=90, optimize=True)
                                    
                                    buffer.seek(0)
                                    image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                                    
                                    # Send via chunking system
                                    send_chunked_image(image_b64, step_index, is_final_step)
                                    
                        except Exception as decode_error:
                            worker_logger.warning(f"Worker {worker_id}: Error decoding step {step_index}: {decode_error}")
                                    
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Error in step callback: {e}")
                error_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='error',
                    data={'error': str(e)}
                )
                result_queue.put(error_result)
            
            return callback_kwargs
        
        def process_streaming_request(gen_request: GenerationRequest):
            """Handle streaming generation request"""
            try:
                pipeline = get_pipeline_for_request(gen_request.request_id)
            except Exception as e:
                error_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='error',
                    data={'error': f"Failed to get pipeline: {str(e)}"}
                )
                result_queue.put(error_result)
                return
            
            try:
                with torch.cuda.device(gpu_id):
                    # Create generator for reproducible results
                    generator = torch.Generator(device=device).manual_seed(int(time.time() * 1000) % (2**32))
                    
                    # Run the pipeline with callback
                    result = pipeline(
                        prompt=gen_request.prompt,
                        negative_prompt=gen_request.negative_prompt,
                        width=gen_request.width,
                        height=gen_request.height,
                        guidance_scale=gen_request.guidance_scale,
                        num_inference_steps=gen_request.num_inference_steps,
                        num_images_per_prompt=gen_request.num_images,
                        generator=generator,
                        callback_on_step_end=step_callback,
                        callback_on_step_end_tensor_inputs=["latents"]
                    )
                
                # Send completion signal
                completion_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='completed',
                    data=None
                )
                result_queue.put(completion_result)
                worker_logger.debug(f"Worker {worker_id}: Streaming request {gen_request.request_id} completed")
                
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Error in streaming request: {e}")
                error_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='error',
                    data={'error': str(e)}
                )
                result_queue.put(error_result)
            finally:
                cleanup_pipeline(gen_request.request_id)
        
        def process_non_streaming_request(gen_request: GenerationRequest):
            """Handle non-streaming generation request"""
            try:
                pipeline = get_pipeline_for_request(gen_request.request_id)
            except Exception as e:
                error_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='error',
                    data={'error': f"Failed to get pipeline: {str(e)}"}
                )
                result_queue.put(error_result)
                return
            
            try:
                with torch.cuda.device(gpu_id):
                    # Create generator for reproducible results
                    generator = torch.Generator(device=device).manual_seed(int(time.time() * 1000) % (2**32))
                    
                    # Run the pipeline
                    result = pipeline(
                        prompt=gen_request.prompt,
                        negative_prompt=gen_request.negative_prompt,
                        width=gen_request.width,
                        height=gen_request.height,
                        guidance_scale=gen_request.guidance_scale,
                        num_inference_steps=gen_request.num_inference_steps,
                        num_images_per_prompt=gen_request.num_images,
                        generator=generator
                    )
                
                # Convert images to base64
                image_data = []
                for image in result.images:
                    buffer = io.BytesIO()
                    image.save(buffer, format='PNG', optimize=True)
                    buffer.seek(0)
                    b64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    image_data.append(b64_image)
                
                # Send result back
                completion_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='completed',
                    data={'images': image_data}
                )
                result_queue.put(completion_result)
                
                worker_logger.debug(f"Worker {worker_id}: Non-streaming request {gen_request.request_id} completed")
                
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Error in non-streaming request: {e}")
                error_result = GenerationResult(
                    request_id=gen_request.request_id,
                    result_type='error',
                    data={'error': str(e)}
                )
                result_queue.put(error_result)
            finally:
                cleanup_pipeline(gen_request.request_id)
        
        # Main worker loop
        worker_logger.info(f"Worker {worker_id} ready to process requests on {device}")
        
        while not shutdown_event.is_set():
            try:
                # Get request from queue with timeout
                gen_request = request_queue.get(timeout=1.0)
                
                worker_logger.info(f"Worker {worker_id}: Processing request {gen_request.request_id}, stream={gen_request.stream}")
                
                if gen_request.stream:
                    process_streaming_request(gen_request)
                else:
                    process_non_streaming_request(gen_request)
                    
            except queue.Empty:
                # No request available, continue loop
                continue
            except Exception as e:
                worker_logger.error(f"Worker {worker_id}: Unexpected error in main loop: {e}")
                
    except Exception as e:
        worker_logger.error(f"Worker {worker_id}: Failed to initialize: {e}")
        return
    
    worker_logger.info(f"Worker {worker_id} shutting down")


class WorkerPool:
    """Manages a pool of persistent worker processes"""
    
    def __init__(self, model_path: str, num_workers: int = NUM_WORKER_PROCESSES):
        self.model_path = model_path
        self.num_workers = num_workers
        
        # Set multiprocessing start method to 'spawn' for CUDA compatibility
        try:
            mp.set_start_method('spawn', force=True)
            logger.info("Set multiprocessing start method to 'spawn' for CUDA compatibility")
        except RuntimeError:
            # If already set, just log the current method
            current_method = mp.get_start_method()
            logger.info(f"Multiprocessing start method already set to: {current_method}")
            if current_method != 'spawn':
                logger.warning("Current start method is not 'spawn' - CUDA workers may fail to initialize")
        
        # Use a multiprocessing context with spawn method
        self.mp_context = mp.get_context('spawn')
        
        # Use the spawn context for creating queues and events
        self.manager = self.mp_context.Manager()
        self.request_queue = self.manager.Queue()
        self.result_queue = self.manager.Queue()
        self.shutdown_event = self.mp_context.Event()
        
        # Shared state for tracking model loading status
        self.worker_model_loaded = self.manager.dict()  # {worker_id: True/False}
        
        self.workers = []
        self.active_requests = {}
        self.lock = threading.Lock()
        
        logger.info(f"Initializing worker pool with {num_workers} workers using 'spawn' method")
        
        # Start worker processes using spawn context
        for i in range(num_workers):
            # Initialize model loading status to False
            self.worker_model_loaded[i] = False
            
            worker = self.mp_context.Process(
                target=worker_process,
                args=(i, model_path, self.request_queue, self.result_queue, self.shutdown_event, self.worker_model_loaded)
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"Started worker process {i} using spawn method")
        
        logger.info(f"Worker pool initialized with {len(self.workers)} workers")
    
    def all_models_loaded(self) -> bool:
        """Check if all workers have successfully loaded their models"""
        if not self.worker_model_loaded:
            return False
        
        # Check if all workers report model loaded = True
        loaded_workers = sum(1 for loaded in self.worker_model_loaded.values() if loaded)
        total_workers = len(self.workers)
        
        logger.debug(f"Model loading status: {loaded_workers}/{total_workers} workers have loaded models")
        return loaded_workers == total_workers and total_workers > 0
    
    async def submit_streaming_request(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 5.0,
        num_inference_steps: int = 50,
        num_images: int = 1
    ):
        """Submit a streaming request to the worker pool"""
        
        request_id = str(uuid.uuid4())[:8]
        
        gen_request = GenerationRequest(
            request_id=request_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            num_images=num_images,
            stream=True
        )
        
        # Track active request
        with self.lock:
            self.active_requests[request_id] = True
        
        # Submit to worker queue
        self.request_queue.put(gen_request)
        logger.info(f"Submitted streaming request {request_id} to worker pool")
        
        try:
            # Stream results
            async for result in self._stream_results(request_id):
                yield result
        finally:
            # Clean up
            with self.lock:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
    
    async def submit_non_streaming_request(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 5.0,
        num_inference_steps: int = 50,
        num_images: int = 1
    ) -> List[str]:
        """Submit a non-streaming request to the worker pool"""
        
        request_id = str(uuid.uuid4())[:8]
        
        gen_request = GenerationRequest(
            request_id=request_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            num_images=num_images,
            stream=False
        )
        
        # Track active request
        with self.lock:
            self.active_requests[request_id] = True
        
        # Submit to worker queue
        self.request_queue.put(gen_request)
        logger.info(f"Submitted non-streaming request {request_id} to worker pool")
        
        try:
            # Wait for completion
            result = await self._wait_for_completion(request_id)
            return result
        finally:
            # Clean up
            with self.lock:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
    
    async def _stream_results(self, request_id: str):
        """Stream results from worker process"""
        while True:
            try:
                # Get result with short timeout
                result = self.result_queue.get(timeout=0.1)
                
                if result.request_id != request_id:
                    # Put it back for another request
                    self.result_queue.put(result)
                    await asyncio.sleep(0.01)
                    continue
                
                if result.result_type == 'error':
                    logger.error(f"Error from worker for request {request_id}: {result.data['error']}")
                    raise Exception(result.data['error'])
                
                if result.result_type == 'completed':
                    logger.debug(f"Streaming request {request_id} completed")
                    break
                
                if result.result_type == 'streaming_step':
                    yield result.data
                
            except queue.Empty:
                # Brief pause if no data available
                await asyncio.sleep(0.05)
    
    async def _wait_for_completion(self, request_id: str):
        """Wait for non-streaming request completion"""
        while True:
            try:
                result = self.result_queue.get(timeout=0.1)
                
                if result.request_id != request_id:
                    # Put it back for another request
                    self.result_queue.put(result)
                    await asyncio.sleep(0.01)
                    continue
                
                if result.result_type == 'error':
                    logger.error(f"Error from worker for request {request_id}: {result.data['error']}")
                    raise Exception(result.data['error'])
                
                if result.result_type == 'completed':
                    logger.debug(f"Non-streaming request {request_id} completed")
                    return result.data.get('images', [])
                
            except queue.Empty:
                await asyncio.sleep(0.05)
    
    def shutdown(self):
        """Shutdown the worker pool"""
        logger.info("Shutting down worker pool...")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for i, worker in enumerate(self.workers):
            worker.join(timeout=10)
            if worker.is_alive():
                logger.warning(f"Force terminating worker {i}")
                worker.terminate()
                worker.join()
        
        logger.info("Worker pool shutdown complete")


# Global worker pool
worker_pool = None

def get_worker_pool():
    global worker_pool
    if worker_pool is None:
        worker_pool = WorkerPool("/gm-models/CogView4-6B")
    return worker_pool


# FastAPI app
app = FastAPI(
    title="CogView4 Image Generation API",
    description="OpenAI-compatible image generation API with persistent worker pool using CogView4",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize the worker pool on startup"""
    logger.info("Starting CogView4 API server...")
    try:
        get_worker_pool()
        logger.info("Worker pool initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize worker pool: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down CogView4 API server...")
    if worker_pool:
        worker_pool.shutdown()
        logger.info("Worker pool shut down successfully")


async def generate_sse_stream(request_data: ImageGenerationRequest):
    """Generate SSE stream of images using worker pool"""
    pool = get_worker_pool()
    
    request_start_time = time.time()
    logger.info(f"Starting SSE stream generation")
    
    try:
        width, height = _parse_size(request_data.size)
        
        # Stream results from worker pool
        async for result in pool.submit_streaming_request(
            prompt=request_data.prompt,
            negative_prompt=request_data.negative_prompt,
            width=width,
            height=height,
            guidance_scale=request_data.guidance_scale,
            num_inference_steps=request_data.num_inference_steps,
            num_images=request_data.n
        ):
            # Send all data directly to client (chunked or not)
            stream_data = StreamingImageData(
                step=result['step'],
                total_steps=request_data.num_inference_steps,
                progress=result['progress'],
                image=result['image'],
                timestamp=result['timestamp'],
                is_final=result['is_final'],
                is_chunked=result.get('is_chunked', False),
                chunk_id=result.get('chunk_id'),
                chunk_index=result.get('chunk_index'),
                total_chunks=result.get('total_chunks')
            )
            
            json_data = stream_data.json()
            
            if result.get('is_chunked', False):
                logger.debug(f"Sending chunk {result['chunk_index'] + 1}/{result['total_chunks']} for step {result['step']}")
            else:
                logger.debug(f"Sending complete image for step {result['step']}")
                
            yield f"data: {json_data}\n\n"
            
            # Small delay to prevent overwhelming the client
            await asyncio.sleep(0.01)  # Reduced delay since we're not buffering
        
        # Send completion signal
        request_duration = time.time() - request_start_time
        logger.info(f"SSE streaming completed in {request_duration:.2f}s")
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        request_duration = time.time() - request_start_time
        logger.error(f"SSE stream error after {request_duration:.2f}s: {e}")
        error_data = {
            "error": str(e),
            "timestamp": time.time()
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/v1/images/generations")
async def create_image(request: ImageGenerationRequest):
    """Create image(s) from text prompt using worker pool"""
    
    request_start_time = time.time()
    logger.info(f"Received image generation request: prompt='{request.prompt[:50]}...', stream={request.stream}, steps={request.num_inference_steps}")
    
    if request.stream:
        # Return SSE stream
        logger.info("Starting streaming response")
        return StreamingResponse(
            generate_sse_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    else:
        # Return standard response using worker pool
        pool = get_worker_pool()
        
        try:
            width, height = _parse_size(request.size)
            
            # Generate using worker pool
            images_b64 = await pool.submit_non_streaming_request(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=width,
                height=height,
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps,
                num_images=request.n
            )
            
            # Convert to response format
            image_data = []
            for b64_image in images_b64:
                if request.response_format == "b64_json":
                    image_data.append(ImageData(b64_json=b64_image))
                else:
                    # For URL format, you'd need to save images and return URLs
                    # For now, just return base64
                    image_data.append(ImageData(b64_json=b64_image))
            
            request_duration = time.time() - request_start_time
            logger.info(f"Non-streaming request completed in {request_duration:.2f}s: generated {len(image_data)} images")
            
            return ImageGenerationResponse(
                created=int(time.time()),
                data=image_data
            )
            
        except Exception as e:
            request_duration = time.time() - request_start_time
            logger.error(f"Request failed after {request_duration:.2f}s: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI compatibility)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "cogview4-6b",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "thudm",
                "permission": [],
                "root": "cogview4-6b",
                "parent": None
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""    
    pool = get_worker_pool() if worker_pool else None
    active_workers = len(pool.workers) if pool else 0
    model_loaded = pool.all_models_loaded() if pool else False
    
    return {
        "status": "healthy", 
        "worker_pool_initialized": pool is not None,
        "active_workers": active_workers,
        "model_loaded": model_loaded,
        "concurrent_support": True,
        "architecture": "Persistent worker pool with from_pipe"
    }


@app.get("/status")
async def status_check():
    """Detailed status endpoint"""
    pool = get_worker_pool() if worker_pool else None
    active_requests = len(pool.active_requests) if pool else 0
    
    return {
        "server": "CogView4 Image Generation API",
        "version": "1.0.0",
        "worker_pool": {
            "initialized": pool is not None,
            "num_workers": len(pool.workers) if pool else 0,
            "active_requests": active_requests,
            "architecture": "Persistent processes + from_pipe"
        },
        "features": [
            "OpenAI-compatible API",
            "Server-Sent Events streaming",
            "Persistent worker pool",
            "Process-based concurrency",
            "Memory-efficient from_pipe",
            "One-time model loading per worker",
            "Intermediate image generation"
        ]
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "CogView4 Image Generation API",
        "version": "1.0.0",
        "description": "OpenAI-compatible image generation API with persistent worker pool using CogView4",
        "endpoints": {
            "generate": "/v1/images/generations",
            "models": "/v1/models",
            "health": "/health",
            "status": "/status",
            "client": "/client.html"
        },
        "features": [
            "OpenAI-compatible API",
            "Server-Sent Events streaming",
            "Persistent worker pool",
            "Efficient model sharing",
            "True concurrent processing"
        ]
    }


@app.get("/client.html", response_class=HTMLResponse)
async def serve_web_client():
    """Serve the web client HTML file"""
    try:
        with open("web_client.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Web client file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving web client: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting CogView4 Image Generation API Server with persistent worker pool...")
    uvicorn.run(
        "cogview4_api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1  # Keep this at 1, concurrency is handled by worker pool
    ) 